"""
测试用例 Service 层。
封装业务逻辑，被 API 层调用。
"""
import json
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.schemas import CaseCreateRequest, CaseUpdateRequest
from app.dao.models import TestCase


class CaseService:
    """测试用例业务逻辑。"""

    @staticmethod
    def create(db: Session, request: CaseCreateRequest) -> TestCase:
        """
        创建测试用例
        1. 将Pydantic模型转为ORM模型
        2. dict/list 字段序列化为 JSON 字符串存储
        3. 持久化到数据库
        """
        case = TestCase(
            name=request.name,
            method=request.method.value,
            url=request.url,
            headers=json.dumps(request.headers) if request.headers else None,
            body=json.dumps(request.body) if request.body else None,
            expected_status=request.expected_status,
            assertions=json.dumps(request.assertions) if request.assertions else None,
            source=request.source.value,
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        return case

    @staticmethod
    def get_by_id(db: Session, case_id: int) -> Optional[TestCase]:
        """根据id查用例"""
        stmt = select(TestCase).where(TestCase.id == case_id)
        result = db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 50) -> list[TestCase]:
        """分页查询所有用例。"""
        stmt = select(TestCase).offset(skip).limit(limit)
        result = db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def update(db: Session, case_id: int, request: CaseUpdateRequest) -> Optional[TestCase]:
        """更新测试用例，且只更新请求中提供的字段"""
        stmt = select(TestCase).where(TestCase.id == case_id)
        case = db.execute(stmt).scalar_one_or_none()
        if not case:
            return None
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field in ("headers", "body"):
                setattr(case, field, json.dumps(value) if value else None)
            elif field == "assertions":
                setattr(case, field, json.dumps(value) if value else None)
            elif field == "method":
                setattr(case, field, value.value if value else None)
            else:
                setattr(case, field, value)

        db.commit()
        db.refresh(case)
        return case

    @staticmethod
    def delete(db: Session, case_id: int) -> bool:
        """删除测试用例"""
        stmt = select(TestCase).where(TestCase.id == case_id)
        case = db.execute(stmt).scalar_one_or_none()
        if not case:
            return False
        db.delete(case)
        db.commit()
        return True