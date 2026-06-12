"""
报告生成服务 —— 汇总执行结果和 AI 分析，输出完整报告
"""

import uuid
from datetime import datetime

from app.service.executor_service import ExecutionReport
from app.core.report import FullReport, ExecutionSummary, CaseReport


class ReportService:
    """生成结构化执行报告"""

    def generate(
            self,
            execution_report: ExecutionReport,
            ai_analyses: list[dict],
            project_name: str,
            model_used: str,
            base_url: str,
    ) -> FullReport:
        """
        将执行结果和 AI 分析合并为完整报告。

        Args:
            execution_report: pytest 执行结果
            ai_analyses: AI 失败归因分析列表
            project_name: 项目名称
            model_used: 使用的 AI 模型
            base_url: 被测系统 URL
        """
        # 建立分析结果索引（按测试名查找）
        analysis_map = {a["test_name"]: a for a in ai_analyses}

        # 组装每个用例的报告
        case_reports = []
        for result in execution_report.results:
            ai_analysis = analysis_map.get(result.name, {})

            case_reports.append(CaseReport(
                name=result.name,
                status=result.status,
                duration=result.duration,
                category=ai_analysis.get("category", "unknown"),
                failure_reason=result.message,
                ai_analysis=ai_analysis,
            ))

        # 统计失败分类
        failure_categories = {}
        for analysis in ai_analyses:
            cat = analysis.get("category", "unknown")
            failure_categories[cat] = failure_categories.get(cat, 0) + 1

        # 计算摘要
        total = execution_report.total
        avg_duration = (
            execution_report.duration / total if total > 0 else 0.0
        )
        pass_rate = (
            execution_report.passed / total if total > 0 else 0.0
        )

        summary = ExecutionSummary(
            total=total,
            passed=execution_report.passed,
            failed=execution_report.failed,
            error=execution_report.error,
            pass_rate=round(pass_rate, 4),
            avg_duration=round(avg_duration, 3),
            total_duration=round(execution_report.duration, 3),
            failure_categories=failure_categories,
        )

        return FullReport(
            report_id=str(uuid.uuid4()),
            project_name=project_name,
            executed_at=datetime.now().isoformat(),
            summary=summary,
            cases=case_reports,
            model_used=model_used,
            base_url=base_url,
        )