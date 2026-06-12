"""
AI失败归因分析 —— 对测试失败进行智能分类和根因分析
"""
import json
import logging
from app.service.ai_service import AIService, AIServiceError

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """你是一位资深测试工程师，擅长分析测试失败的根本原因。

对于每一个失败的测试用例，你需要判断失败属于哪种分类：
1. api_bug: API接口存在缺陷（返回了错误的状态码、响应体有误、缺少字段等）
2. case_bug: 测试用例本身有问题（断言写错、期望值不合理、请求参数构造有误）
3. env_issue: 环境问题（连接超时、服务未启动、DNS解析失败、端口被占用）
4. data_issue: 数据问题（依赖的测试数据不存在、数据被其他测试污染、前置数据未准备）

判断原则：
- 如果状态码是 5xx 且请求参数合理 → 大概率 api_bug
- 如果状态码是 4xx 但测试设计预期不当 → case_bug
- 如果出现 ConnectionError/Timeout → env_issue
- 如果返回"not found"且数据应该提前准备 → data_issue

请输出 JSON 格式的分析结果，格式如下：
{"analyses": [{"test_name": "...", "category": "api_bug|case_bug|env_issue|data_issue", "root_cause": "一句话根因", "suggestion": "修复建议", "confidence": 0.0-1.0}, ...]}
"""


class FailureAnalyzer:
    """测试失败归因分析器"""

    def __init__(self, model_key: str = "deepseek"):
        self.ai_service = AIService(model_key=model_key)

    def analyze(self, failures: list[dict]) -> list[dict]:
        """
        分析一批测试失败。

        Args:
            failures: 失败用例列表，每个元素格式：
                {
                    "name": "test_POST_register_empty_username",
                    "expected_status": 400,
                    "actual_status": 500,
                    "error_message": "AssertionError: ...",
                    "response_body": "{...}",
                    "request_info": {"method": "POST", "url": "...", "body": {...}}
                }

        Returns:
            分析结果列表
        """
        if not failures:
            return []

        failure_descriptions = []
        for f in failures:
            desc = f"""
测试名: {f['name']}
请求: {f.get('request_info', {}).get('method', '?')} {f.get('request_info', {}).get('url', '?')}
请求体: {json.dumps(f.get('request_info', {}).get('body', {}), ensure_ascii=False)[:200]}
期望状态码: {f.get('expected_status', '?')}
实际状态码: {f.get('actual_status', '?')}
错误信息: {f.get('error_message', '')[:300]}
响应体: {f.get('response_body', '')[:200]}
"""
            failure_descriptions.append(desc)

        user_message = f"""请分析以下 {len(failures)} 个测试失败的根本原因：

{"---".join(failure_descriptions)}
"""

        messages = [
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        try:
            response = self.ai_service._call_with_retry(messages)
            content = response.choices[0].message.content
            if not content:
                return []
            data = json.loads(content)
            return data.get("analyses", [])

        except (AIServiceError, json.JSONDecodeError, Exception) as e:
            logger.error(f"失败分析异常: {e}")
            return []
