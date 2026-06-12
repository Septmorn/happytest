"""执行报告数据模型"""
from dataclasses import dataclass, field


@dataclass
class CaseReport:
    """"单用例报告"""
    name: str
    status: str  # passed | failed | error
    duration: float  # 秒
    category: str  # happy_path | boundary | error | auth_failure
    failure_reason: str = ""
    ai_analysis: dict = field(default_factory=dict)
    # ai_analysis 示例: {"category": "api_bug", "root_cause": "...", "suggestion": "..."}


@dataclass
class ExecutionSummary:
    """执行摘要"""
    total: int
    passed: int
    failed: int
    error: int
    pass_rate: float  # 0.0 ~ 1.0
    avg_duration: float  # 秒
    total_duration: float  # 秒
    failure_categories: dict  # {"api_bug": 2, "case_bug": 1, ...}


@dataclass
class FullReport:
    """完整执行报告"""
    report_id: str
    project_name: str
    executed_at: str
    summary: ExecutionSummary
    cases: list[CaseReport]
    model_used: str  # 使用的 AI 模型
    base_url: str  # 被测系统 URL