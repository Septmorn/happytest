"""
闭环测试管道 API —— 支持前端一键触发完整流程
"""
import logging
import uuid

from _pytest.pytester import RunResult
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])
logger = logging.getLogger(__name__)

# ─── 请求/响应模型 ───

class PipeLineRequest(BaseModel):
    """闭环执行请求"""
    api_doc: str = Field(..., min_length=10, description="API文档内容")
    base_url: str = Field(..., description="被测服务地址")
    model: str = Field(default="deepseek", description="AI模型")
    project_name: str = Field(default="HappyTest", description="项目名称")


class PipeLineStatusResponse(BaseModel):
    """管道状态响应"""
    task_id: str
    status: str  # pending | generating | executing | analyzing | completed | failed
    progress: dict | None = None
    result: dict | None = None
    error: dict | None = None

# ─── 内存存储（开发阶段） ───

_pipeline_tasks: dict[str, dict] = {}


def _run_pipeline(task_id: str, request: PipeLineRequest):
    """后台执行完整闭环流程"""
    from app.service.ai_service import AIService, AIServiceError
    from app.service.test_generator import TestFileGenerator
    from app.service.executor_service import ExecutorService
    from app.service.failure_analyzer import FailureAnalyzer
    from app.service.report_service import ReportService

    task = _pipeline_tasks[task_id]

    try:
        # Step 1: AI 生成测试用例
        task["status"] = "generating"
        task["progress"] = {"step": 1, "total": 4, "message": "AI 正在生成测试用例..."}

        ai_service = AIService(model_key=request.model)
        cases = ai_service.generate_test_cases(request.api_doc)

        task["progress"]["message"] = f"生成了 {len(cases)} 个测试用例"

        # Step 2: 渲染测试文件并执行
        task["status"] = "executing"
        task["progress"] = {"step": 2, "total": 4, "message": "正在执行测试..."}

        generator = TestFileGenerator()
        test_file = generator.generate(
            cases=cases,
            base_url=request.base_url,
            project_name=request.project_name,
        )

        executor = ExecutorService()
        report = executor.execute(test_file, timeout=60)

        # Step 3: AI分析失败用例
        task["status"] = "analyzing"
        task["progress"] = {"step": 3, "total": 4, "message": "AI 正在分析失败原因..."}

        failures = []
        for r in report.results:
            if r.status == "failed":
                case_data = next((c for c in cases if c["name"] == r.name), {})
                failures.append({
                    "name": r.name,
                    "expected_status": case_data.get("expected_status", "?"),
                    "actual_status": "unknown",
                    "error_message": r.message,
                    "response_body": "",
                    "request_info": {
                        "method": case_data.get("method", "?"),
                        "url": case_data.get("url", "?"),
                        "body": case_data.get("body", {}),
                    },
                })

        analyses = []
        if failures:
            analyzer = FailureAnalyzer(model_key=request.model)
            analyses = analyzer.analyze(failures)

        # Step 4: 生成报告
        task["progress"] = {"step": 4, "total": 4, "message": "正在生成报告..."}

        report_svc = ReportService()
        full_report = report_svc.generate(
            execution_report=report,
            ai_analyses=analyses,
            project_name=request.project_name,
            model_used=request.model,
            base_url=request.base_url,
        )

        # 完成
        task["status"] = "completed"
        task["progress"] = {"step": 4, "total": 4, "message": "完成"}
        task["result"] = {
            "summary": {
                "total": full_report.summary.total,
                "passed": full_report.summary.passed,
                "failed": full_report.summary.failed,
                "error": full_report.summary.error,
                "pass_rate": full_report.summary.pass_rate,
                "duration": full_report.summary.total_duration,
                "failure_categories": full_report.summary.failure_categories,
            },
            "cases": [
                {
                    "name": c.name,
                    "status": c.status,
                    "duration": c.duration,
                    "category": c.category,
                    "failure_reason": c.failure_reason,
                    "ai_analysis": c.ai_analysis,
                }
                for c in full_report.cases
            ],
            "test_cases_generated": [
                {
                    "name": c["name"],
                    "method": c["method"],
                    "url": c["url"],
                    "expected_status": c["expected_status"],
                    "category": c.get("category", ""),
                    "description": c.get("description", ""),
                }
                for c in cases
            ],
        }

        # 清理临时文件
        generator.cleanup(test_file)
    except AIServiceError as e:
        task["status"] = "failed"
        task["error"] = f"AI 服务错误: {str(e)}"

    except Exception as e:
        task["status"] = "failed"
        task["error"] = f"执行异常: {str(e)}"
        logger.exception(f"Pipeline {task_id} failed")

# ─── 路由 ───

@router.post("/run", response_model=PipeLineStatusResponse, status_code=202)
def run_pipeline(request: PipeLineRequest, background_tasks: BackgroundTasks):
    """启动闭环测试管道"""
    task_id = str(uuid.uuid4())
    _pipeline_tasks[task_id] = {
        "status": "pending",
        "progress": None,
        "result": None,
        "error": None,
    }

    background_tasks.add_task(_run_pipeline, task_id, request)

    return PipeLineStatusResponse(task_id=task_id, status="pending")

@router.get("/status/{task_id}", response_model=PipeLineStatusResponse)
def get_pipeline_status(task_id: str):
    """查询管道执行状态"""
    task = _pipeline_tasks.get(task_id)
    if not task:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="任务不存在")

    return PipeLineStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        result=task["result"],
        error=task["error"],
    )





