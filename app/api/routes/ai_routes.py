"""
AI 用例生成 API 路由
"""

import uuid
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dao.database import get_db, SessionLocal
from app.dao.models import TestCase, Task, TaskStatus
from app.service.ai_service import AIService, AIServiceError, MODEL_REGISTRY

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["AI"])


# ─────────────── Request / Response Models ───────────────

class GenerateRequest(BaseModel):
    """用例生成请求"""
    api_doc: str = Field(..., min_length=10, description="API文档内容")
    model: str = Field(default="deepseek", description="使用的模型")


class GenerateResponse(BaseModel):
    """用例生成响应"""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """任务状态查询响应"""
    task_id: str
    status: str
    result: dict | None = None
    error: str | None = None


# ─────────────── 后台任务函数 ───────────────

def _run_generation(task_id: str, api_doc: str, model_key: str):
    """
    后台执行用例生成。
    注意：后台任务自己创建 db session，不复用路由层的 session。
    """
    import json
    db = SessionLocal()
    try:
        stmt = select(Task).where(Task.id == task_id)
        task = db.execute(stmt).scalar_one_or_none()
        task.status = TaskStatus.PROCESSING.value
        db.commit()

        service = AIService(model_key=model_key)
        test_cases = service.generate_test_cases(api_doc)

        for case_data in test_cases:
            db_case = TestCase(
                name=case_data["name"],
                method=case_data["method"],
                url=case_data["url"],
                headers=json.dumps(case_data.get("headers")) if case_data.get("headers") else None,
                body=json.dumps(case_data.get("body")) if case_data.get("body") else None,
                expected_status=case_data["expected_status"],
                assertions=json.dumps(case_data.get("assertions")) if case_data.get("assertions") else None,
                category=case_data.get("category"),
                description=case_data.get("description"),
                priority=case_data.get("priority", "medium"),
                source="ai",
            )
            db.add(db_case)

        task.status = TaskStatus.COMPLETED.value
        task.result = {"total_cases": len(test_cases)}
        db.commit()
        logger.info(f"任务 {task_id} 完成，生成 {len(test_cases)} 个用例")

    except AIServiceError as e:
        task.status = TaskStatus.FAILED.value
        task.error = str(e)
        db.commit()
        logger.error(f"任务 {task_id} 失败: {e}")

    except Exception as e:
        task.status = TaskStatus.FAILED.value
        task.error = f"未预期的错误: {str(e)}"
        db.commit()
        logger.exception(f"任务 {task_id} 异常")

    finally:
        db.close()


# ─────────────── API 路由 ───────────────

@router.post("/generate", response_model=GenerateResponse, status_code=202)
def generate_test_cases(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """启动 AI 用例生成任务，立即返回 task_id，后台异步执行。"""
    if request.model not in MODEL_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的模型: {request.model}，可选: {list(MODEL_REGISTRY.keys())}",
        )

    task_id = str(uuid.uuid4())
    task = Task(id=task_id, type="ai_generate", status=TaskStatus.PENDING.value)
    db.add(task)
    db.commit()

    background_tasks.add_task(_run_generation, task_id, request.api_doc, request.model)

    return GenerateResponse(
        task_id=task_id,
        status="processing",
        message="用例生成已开始，请通过 task_id 查询进度",
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """查询任务执行状态"""
    stmt = select(Task).where(Task.id == task_id)
    task = db.execute(stmt).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        result=task.result,
        error=task.error,
    )