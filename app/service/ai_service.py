"""
AI服务层，负责与LLM交互，生成结构化的测试用例。
核心技术：OpenAPI SDK + Function Calling
"""
import json
import logging
from dataclasses import dataclass
import time

from openai import OpenAI, RateLimitError, APITimeoutError, APIError

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 模型配置
# ─────────────────────────────────────────────
@dataclass
class ModelConfig:
    """模型配置信息"""
    name: str           # 模型标识符，比如"deepseek-v4-flash"
    base_url: str       # API基础URL
    api_key: str        # API秘钥
    max_tokens: int     # 最大输出token数
    temperature: float  # 温度参数


# 模型注册表：支持多模态动态切换
MODEL_REGISTRY: dict[str, ModelConfig] = {
    "deepseek": ModelConfig(
        name=settings.deepseek_model,
        base_url=settings.deepseek_base_url,
        api_key=settings.deepseek_api_key,
        max_tokens=settings.ai_max_tokens,
        temperature=settings.ai_temperature,
    )
}

# ─────────────────────────────────────────────
# System Prompt
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """你是一位拥有10年经验的资深QA工程师，专精API自动化测试。
你的任务是：分析用户提供的API文档，生成全面的测试用例集。
生成规则：
1. 每个API至少生成以下四类用例：
   - happy_path: 正常参数，验证成功响应
   - boundary: 边界值（空字符串、最大长度、最小值/最大值、特殊字符）
   - error: 异常输入（类型错误、格式错误、缺少必填字段）
   - auth_failure: 认证失败（无token、过期token、无权限）
2. 用例命名规范：{HTTP方法}_{路径关键词}_{场景描述}
   示例：POST_register_success, POST_register_empty_username
3. 对于每个用例，必须指定精确的请求参数和期望结果。
4. 边界值要具体：
   - 字符串：空串、单字符、超长(256+字符)、含特殊字符
   - 数字：0、-1、最大值、浮点数
   - 必填字段：逐一缺省测试
5. 输出格式要求：直接输出一个 JSON 对象，格式如下（不要输出多余的文字说明）：
{"test_cases": [{"name": "...", "method": "...", "url": "...", "headers": {...}, "body": {...}, "expected_status": 200, "assertions": [...], "category": "...", "description": "...", "priority": "high/medium/low"}, ...]}
6. JSON 值必须是字面量，禁止使用编程表达式（如 "a" * 10 或字符串拼接），超长字符串直接写出实际内容或用省略代替。
"""

# ─────────────────────────────────────────────
# AI Service 主类
# ─────────────────────────────────────────────

class AIService:
    """
    AI服务，封装与LLM的交互逻辑。
    使用方法：
        service = AIService(model_key="deepseek")
        cases = await service.generate_test_cases(api_doc_text)
    """
    def __init__(self, model_key: str = "deepseek"):
        """
        初始化AI服务
        """
        if model_key not in MODEL_REGISTRY:
            raise ValueError(
                f"未知模型：{model_key}, 可选：{list(MODEL_REGISTRY.keys())}"
            )
        self.model_config = MODEL_REGISTRY[model_key]

        # 使用OpenAI SDK，通过base_url切换不同模型供应商(deepseek兼容OpenAI API 格式)
        self.client = OpenAI(
            api_key=self.model_config.api_key,
            base_url=self.model_config.base_url,
        )

        logger.info(f"AIService初始化完成，使用模型：{self.model_config.name}")

    def generate_test_cases(self, api_doc: str) -> list[dict]:
        """
        核心方法：根据API文档生成测试用例
        :param api_doc: API文档文本(OpenAPI JSON 或纯文本描述)
        :return: 测试用例列表，每个元素是一个dict
        :raise: AIServiceError: LLM 调用失败或返回格式异常
        """
        messages = self._build_messages(api_doc)
        response = self._call_with_retry(messages)
        return self._parse_response(response)

    def _build_messages(self, api_doc: str) -> list[dict]:
        """构建发送给LLM的消息列表"""
        user_content = f"""请分析以下API文档，生成全面的测试用例集。
## API 文档内容：
{api_doc}

## 要求：
- 覆盖 happy_path、boundary、error、auth_failure 四类场景
- 每类至少2个用例
- 直接输出 JSON 对象，格式为 {{"test_cases": [...]}}，不要输出其他内容
"""
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

    def _call_with_retry(self, messages: list[dict], max_retries: int = 3) -> object:
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_config.name,
                    messages=messages,
                    max_tokens=self.model_config.max_tokens,
                    temperature=self.model_config.temperature,
                    response_format={"type": "json_object"},
                )
                # 官方文档提示 JSON Output 有概率返回空 content，遇到时重试
                if not response.choices[0].message.content:
                    logger.warning(f"LLM 返回空 content，重试 (第{attempt + 1}次)")
                    continue
                return response
            except RateLimitError as e:
                wait_time = 2 ** attempt * 3
                logger.warning(
                    f"触发频率限制，{wait_time}秒后重试"
                    f"(第{attempt + 1}次，共{max_retries}次)"
                )
                time.sleep(wait_time)

            except APITimeoutError as e:
                wait_time = 2 ** attempt * 3
                logger.warning(f"请求超时，{wait_time}秒后重试")
                time.sleep(wait_time)

            except APIError as e:
                logger.error(f"API 错误: {e}")
                raise AIServiceError(f"LLM API 调用失败: {e}") from e

        raise AIServiceError(f"LLM 调用在 {max_retries} 次重试后仍然失败")

    def _parse_response(self, response) -> list[dict]:
        """解析 LLM 返回的 JSON 结果，提取测试用例列表。"""
        content = response.choices[0].message.content
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # response_format=json_object 理论上不会到这里，加防御
            data = self._try_fix_truncated_json(content)
            if data is None:
                raise AIServiceError("LLM 返回的 JSON 格式无效")

        if isinstance(data, dict):
            test_cases = data.get("test_cases", [])
        elif isinstance(data, list):
            test_cases = data
        else:
            raise AIServiceError("解析结果格式不符合预期")

        if not test_cases:
            raise AIServiceError("LLM 返回了空的测试用例列表")

        valid_cases = [
            case for case in test_cases
            if all(f in case for f in ["name", "method", "url", "expected_status", "category"])
        ]

        logger.info(f"解析完成: {len(valid_cases)}/{len(test_cases)} 个用例有效")
        return valid_cases

    @staticmethod
    def _try_fix_truncated_json(text: str):
        """尝试修复被 max_tokens 截断的 JSON，返回解析后的对象或 None。"""
        # 策略：找到最后一个完整的 "}," 或 "}" 块，截断后补全外层括号
        # 找 "test_cases" 数组中最后一个完整对象的结尾
        last_obj_end = text.rfind('},')
        if last_obj_end == -1:
            last_obj_end = text.rfind('}')
        if last_obj_end == -1:
            return None

        # 从开头到最后一个完整对象结尾，补上 ]}
        truncated = text[:last_obj_end + 1]
        for suffix in (']}\n', ']}'):
            try:
                return json.loads(truncated + suffix)
            except json.JSONDecodeError:
                continue
        # 可能外层没有 {"test_cases": ...}，直接是数组
        for suffix in (']\n', ']'):
            try:
                return json.loads(truncated + suffix)
            except json.JSONDecodeError:
                continue
        return None


class AIServiceError(Exception):
    """AI 服务异常"""
    pass