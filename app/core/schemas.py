from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class HttpMethod(str, Enum):
    """HTTP 方法枚举。继承 str 使其可直接序列化为字符串。"""
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'
    PATCH = 'PATCH'

class CaseSource(str, Enum):
    """用例来源：手动创建 or AI 生成。"""
    MANUAL = 'manual'
    AI = 'ai'

class ExecutionStatus(str, Enum):
    """执行状态。"""
    PASS = 'pass'
    FAIL = 'fail'
    ERROR = 'error'


# ===== 测试用例 Schemas =====
class CaseCreateRequest(BaseModel):
    """创建测试用例的请求体。"""
    name: str = Field(..., min_length=1, max_length=200, description="用例名称")
    method: HttpMethod = Field(..., description="HTTP方法")
    url: str = Field(..., min_length=1, description="请求URL")
    headers: Optional[dict] = Field(default=None, description="请求头")
    body: Optional[dict] = Field(default=None, description="请求体")
    expected_status: int = Field(default=200, ge=100, le=599, description="期望状态码")
    assertions: Optional[list[str]] = Field(default=None, description="断言表达式列表")
    source: CaseSource = Field(default=CaseSource.MANUAL, description="用例来源")


class CaseUpdateRequest(BaseModel):
    """更新测试用例的请求体。所有字段可选（部分更新）。"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    method: Optional[HttpMethod] = None
    url: Optional[str] = Field(default=None, min_length=1)
    headers: Optional[dict] = None
    body: Optional[dict] = None
    expected_status: Optional[int] = Field(default=None, ge=100, le=599)
    assertions: Optional[list[str]] = None


class CaseResponse(BaseModel):
    """测试用例响应体。"""
    id: int
    name: str
    method: HttpMethod
    url: str
    headers: Optional[dict] = None
    body: Optional[dict] = None
    expected_status: int
    assertions: Optional[list[str]] = None
    source: CaseSource
    category: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}  # 允许从 ORM 对象直接转换


# ===== 执行记录 Schemas =====

class ExecutionResponse(BaseModel):
    """执行记录响应体。"""
    id: int
    case_id: int
    status: ExecutionStatus
    response_body: Optional[str] = None
    duration_ms: int
    error_message: Optional[str] = None
    executed_at: datetime

    model_config = {"from_attributes": True}