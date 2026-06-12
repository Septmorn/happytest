"""
测试执行服务 —— 负责运行pytest并收集结构化结果
"""
import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """单个测试用例的执行结果"""
    name: str
    status: str         # "passed" | "failed" | "error"
    duration: float     # 执行耗时（秒）
    message: str = ""   # 失败/错误信息
    stdout: str = ""    # 标准输出


@dataclass
class ExecutionReport:
    """一次执行的完整报告"""
    total: int = 0
    passed: int = 0
    failed: int = 0
    error: int = 0
    duration: float = 0.0
    results: list[TestResult] = field(default_factory=list)
    executed_at: str = ""
    test_file: str = ""


class ExecutorService:
    """
    pytest执行器。
    1、调用pytest执行生成的测试文件；
    2、通过pytest-json-report收集结构化结果
    3、解析结果为统一的ExecutionReport格式
    """

    def __init__(self, python_path: str = "python"):
        """
        :param python_path: Python 解释器路径（需要安装了 pytest）
        """
        self.python_path = python_path

    def execute(self, test_file: str, timeout: int = 120) -> ExecutionReport:
        """
        执行测试文件并返回结果报告。
        :param test_file: pytest测试文件路径
        :param timeout: 超时时间（默认120秒）
        :return: ExecutionReport 结构化报告
        """
        # JSON 报告输出路径
        report_path = Path(tempfile.gettempdir()) / "happytest_runs" / "report.json"

        # 构建pytest命令
        cmd = [
            self.python_path, "-m", "pytest",
            test_file,
            f"--json-report-file={report_path}",
            "--json-report",    # 启用 JSON 报告插件
            "-v",               # 详细输出
            "--tb=short",       # 简短的 traceback
            "--no-header",      # 不输出 pytest header
            "-q",               # 安静模式
        ]

        logger.info(f"执行命令： {''.join(cmd)}")
        try:
            # 执行pytest
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path(test_file).parent),  # 在测试文件所在目录执行
            )

            logger.info(f"pytest 退出码: {result.returncode}")

            # 解析 JSON 报告
            if report_path.exists():
                report = self._parse_json_report(report_path)
            else:
                # JSON 报告未生成，从 stdout 解析
                logger.warning("JSON 报告文件未生成，使用 stdout 解析")
                report = self._parse_from_stdout(result)

            report.test_file = test_file
            report.executed_at = datetime.now().isoformat()

            return report

        except subprocess.TimeoutExpired:
            logger.error(f"pytest 执行超时（{timeout}秒）")
            return ExecutionReport(
                total=0,
                error=1,
                duration=float(timeout),
                results=[TestResult(
                    name="TIMEOUT",
                    status="error",
                    duration=float(timeout),
                    message=f"测试执行超时，超过{timeout}秒限制",
                )],
                executed_at=datetime.now().isoformat(),
                test_file=test_file,
            )

        except Exception as e:
            logger.exception("pytest 执行异常")
            return ExecutionReport(
                total=0,
                error=1,
                results=[TestResult(
                    name="CRASH",
                    status="error",
                    duration=0.0,
                    message=f"执行器异常: {str(e)}",
                )],
                executed_at=datetime.now().isoformat(),
                test_file=test_file,
            )

        finally:
            # 清理报告文件
            if report_path.exists():
                report_path.unlink()

    def _parse_json_report(self, report_path: Path) -> ExecutionReport:
        """
        解析 pytest-json-report 生成的 JSON 文件。
        JSON 报告结构示例：
        {
            "duration": 2.5,
            "summary": {"total": 8, "passed": 6, "failed": 2},
            "tests": [
                {
                    "nodeid": "test_file.py::test_name",
                    "outcome": "passed",
                    "duration": 0.3,
                    "call": {"longrepr": "AssertionError: ..."}
                }
            ]
        }
        """
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        summary = data.get("summary", {})
        tests = data.get("tests", [])

        results = []
        for test in tests:
            # 提取测试名(去掉文件路径前缀)
            nodeid = test.get("nodeid", "unknown")
            name = nodeid.split("::")[-1] if "::" in nodeid else nodeid

            # 提取失败信息
            message = ""
            if test.get("outcome") in ("failed", "error"):
                call_info = test.get("call", {})
                message = call_info.get("longrepr", "")
                # 截断过长的错误信息
                if len(message) > 500:
                    message = message[:500] + "...(truncated)"

            results.append(TestResult(
                name=name,
                status=test.get("outcome", "unknown"),
                duration=test.get("duration", 0.0),
                message=message,
                stdout=test.get("stdout", ""),
            ))

        return ExecutionReport(
            total=summary.get("total", len(tests)),
            passed=summary.get("passed", 0),
            failed=summary.get("failed", 0),
            error=summary.get("error", 0),
            duration=data.get("duration", 0.0),
            results=results,
        )

    def _parse_from_stdout(self, result: subprocess.CompletedProcess) -> ExecutionReport:
        """当JSON报告不可用时，从stdout粗略解析结果"""
        output = result.stdout + result.stderr

        # 简单计数
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        error = output.count(" ERROR")

        return ExecutionReport(
            total=passed + failed + error,
            passed=passed,
            failed=failed,
            error=error,
            results=[TestResult(
                name="aggregate",
                status="failed" if (failed + error) > 0 else "passed",
                duration=0.0,
                message=output[-1000:] if output else "无输出",
            )],
        )