from app.service.ai_service import AIService

api_doc_text = """## API: 用户注册
- 路径: POST /api/users/register
- 描述: 注册新用户账号

### 请求参数 (JSON Body):
- username: string, 必填, 3-20字符, 只允许字母数字下划线
- email: string, 必填, 合法邮箱格式
- password: string, 必填, 6-128字符, 至少包含一个数字和一个字母

### 请求头:
- Content-Type: application/json

### 成功响应 (201):
{
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "created_at": "2024-01-01T00:00:00Z"
}

### 错误响应:
- 400: 参数验证失败 {"detail": "具体错误信息"}
- 409: 用户名或邮箱已存在 {"detail": "username already exists"}
- 422: 请求体格式错误
"""

service = AIService(model_key="deepseek")
cases = service.generate_test_cases(api_doc_text)

print(f"\n共生成 {len(cases)} 个用例:\n")
for case in cases:
    print(f"[{case['category']}] {case['name']}")
