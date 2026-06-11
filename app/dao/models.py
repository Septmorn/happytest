import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.dao.database import Base


class TestCase(Base):
    """测试用例表"""
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), comment="用例名称")
    method: Mapped[str] = mapped_column(String(10), comment="HTTP 方法")
    url: Mapped[str] = mapped_column(String(500), comment="请求 URL")
    headers: Mapped[Optional[str]] = mapped_column(Text, default=None, comment="请求头 JSON")
    body: Mapped[Optional[str]] = mapped_column(Text, default=None, comment="请求体 JSON")
    expected_status: Mapped[int] = mapped_column(default=200, comment="期望状态码")
    assertions: Mapped[Optional[str]] = mapped_column(Text, default=None, comment="检查响应体中的字段值")
    source: Mapped[str] = mapped_column(String(20), default="manual", comment="区分 手动创建/AI生成")
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), comment="创建时间"
    )

    executions: Mapped[list["Execution"]] = relationship(
        back_populates="test_case", cascade="all, delete-orphan"
    )

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

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"), comment="关联用例ID")
    status: Mapped[str] = mapped_column(String(10), comment="执行状态: pass/fail/error")
    response_body: Mapped[Optional[str]] = mapped_column(Text, default=None, comment="实际响应体")
    duration_ms: Mapped[int] = mapped_column(default=0, comment="执行耗时(毫秒)")
    error_message: Mapped[Optional[str]] = mapped_column(Text, default=None, comment="错误信息")
    executed_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc), comment="执行时间"
    )

    test_case: Mapped["TestCase"] = relationship(back_populates="executions")