import json
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.dao.database import Base


class TestCase(Base):
    """测试用例表"""
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, comment="用例名称")
    method = Column(String(10), nullable=False, comment="HTTP 方法")
    url = Column(String(500), nullable=False, comment="请求 URL")
    headers = Column(Text, nullable=True, comment="请求头 JSON")
    body = Column(Text, nullable=True, comment="请求体 JSON")
    expected_status = Column(Integer, nullable=False, default=200, comment="期望状态码")
    assertions = Column(Text, nullable=True, comment="断言列表 JSON")
    source = Column(String(20), nullable=False, default="manual", comment="来源: manual/ai")
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="创建时间"
    )

    # 关联：一个用例有多条执行记录
    executions = relationship("Execution", back_populates="test_case", cascade="all, delete-orphan")

    def get_headers_dict(self) -> dict | None:
        if self.headers:
            return json.loads(self.headers)
        return None

    def get_body_dict(self) -> dict | None:
        if self.body:
            return json.loads(self.body)
        return None

    def get_assertions_list(self) -> list[str] | None:
        if self.assertions:
            return json.loads(self.assertions)
        return None


class Execution(Base):
    """测试执行记录表。每次执行一个用例产生一条记录。"""

    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("test_cases.id"), nullable=False, comment="关联用例ID")
    status = Column(String(10), nullable=False, comment="执行状态: pass/fail/error")
    response_body = Column(Text, nullable=True, comment="实际响应体")
    duration_ms = Column(Integer, nullable=False, default=0, comment="执行耗时(毫秒)")
    error_message = Column(Text, nullable=True, comment="错误信息")
    executed_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="执行时间"
    )

    # 反向关联：通过 execution.test_case 访问关联的用例
    test_case = relationship("TestCase", back_populates="executions")