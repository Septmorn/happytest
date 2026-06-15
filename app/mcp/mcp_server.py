"""
HappyTest MCP Server
让 AI 客户端（Claude Code、Cursor 等）能够直接调用 HappyTest 的测试能力。

启动方式（stdio 模式）:
    python -m app.mcp.mcp_server
"""
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
    CallToolResult,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("happytest-mcp")

# 创建MCP Server实例
server = Server("happytest")

# ============================================================
# 工具定义：通过 list_tools 让客户端发现我们提供的能力
# ============================================================
@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    返回本Server暴露的所有工具
    每个工具包含name、description和inputSchema（JSON Schema格式）
    AI客户端会根据description决定何时使用哪个工具
    """
    return [
        Tool(
            name="query_test_cases",
            description=(
                "查询 HappyTest 平台中的测试用例。"
                "可按项目名、状态（passed/failed/pending）、"
                "来源（ai/manual）筛选，支持分页。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "项目名称，必填",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["passed", "failed", "pending"],
                        "description": "按执行状态筛选",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["ai", "manual"],
                        "description": "按来源筛选：ai 为 AI 生成，manual 为手动编写",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量上限，默认 20",
                        "default": 20,
                    },
                },
                "required": ["project_name"],
            },
        ),
        Tool(
            name="run_test_suite",
            description=(
                "执行 HappyTest 平台中的测试套件。"
                "从数据库读取已有测试用例，渲染为 pytest 文件并执行。"
                "需要指定被测服务地址。返回执行摘要。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "项目名称",
                    },
                    "base_url": {
                        "type": "string",
                        "description": "被测服务地址，如 http://127.0.0.1:8080",
                    },
                },
                "required": ["project_name"],
            },
        ),
        Tool(
            name="ask_knowledge_base",
            description=(
                "查询 HappyTest 的 RAG 知识库。"
                "可以询问测试最佳实践、接口测试方法、"
                "常见 Bug 模式等测试相关问题。返回答案和引用来源。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "要查询的问题",
                    },
                },
                "required": ["question"],
            },
        ),
    ]

# ============================================================
# 工具实现：处理 AI 客户端的调用请求
# ============================================================

async def _handle_query_test_cases(args: dict[str, Any]) -> dict:
    """查询测试用例（从 MySQL 数据库读取）。"""
    from app.dao.database import SessionLocal
    from app.service.case_service import CaseService

    db = SessionLocal()
    try:
        cases = CaseService.list_all(db, skip=0, limit=args.get("limit", 20))
        return {
            "total": len(cases),
            "project": args["project_name"],
            "filters": {
                "status": args.get("status", "all"),
                "source": args.get("source", "all"),
            },
            "cases": [
                {
                    "id": c.id,
                    "name": c.name,
                    "method": c.method,
                    "url": c.url,
                    "expected_status": c.expected_status,
                    "source": c.source,
                    "category": c.category,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in cases
            ],
        }
    finally:
        db.close()


async def _handle_run_test_suite(args: dict[str, Any]) -> dict:
    """
    执行测试套件。
    从数据库查询用例，渲染为 pytest 文件并执行。
    """
    from app.dao.database import SessionLocal
    from app.service.case_service import CaseService
    from app.service.test_generator import TestFileGenerator
    from app.service.executor_service import ExecutorService

    db = SessionLocal()
    try:
        cases = CaseService.list_all(db, skip=0, limit=100)
        if not cases:
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "error": 0,
                "duration_seconds": 0.0,
                "message": "数据库中没有测试用例，请先通过 AI 生成或手动添加。",
                "failures": [],
            }

        case_dicts = [
            {
                "name": c.name,
                "method": c.method,
                "url": c.url,
                "headers": c.get_headers_dict() or {},
                "body": c.get_body_dict(),
                "expected_status": c.expected_status,
                "category": c.category or "",
                "description": c.description or "",
            }
            for c in cases
        ]
    finally:
        db.close()

    base_url = args.get("base_url", "http://127.0.0.1:8080")
    project_name = args.get("project_name", "HappyTest")

    generator = TestFileGenerator()
    test_file = generator.generate(
        cases=case_dicts,
        base_url=base_url,
        project_name=project_name,
    )

    executor = ExecutorService()
    report = executor.execute(test_file, timeout=60)
    generator.cleanup(test_file)

    failures = [
        {"name": r.name, "error": r.message[:200]}
        for r in report.results if r.status == "failed"
    ]

    return {
        "total": report.total,
        "passed": report.passed,
        "failed": report.failed,
        "error": report.error,
        "duration_seconds": report.duration,
        "failures": failures,
    }


async def _handle_ask_knowledge_base(args: dict[str, Any]) -> dict:
    """
    查询 RAG 知识库。
    """
    return {
        "question": args["question"],
        "answer": "RAG 知识库尚未配置，请先完成知识库搭建后再使用此工具。",
        "sources": [],
        "confidence": 0.0,
    }


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """
    分发工具调用到具体的处理函数
    MCP SDK 会自动验证 arguments 是否符合 inputSchema
    """
    logger.info(f"Tool called: {name}, args: {arguments}")

    try:
        if name == "query_test_cases":
            result = await _handle_query_test_cases(arguments)
        elif name == "run_test_suite":
            result = await _handle_run_test_suite(arguments)
        elif name == "ask_knowledge_base":
            result = await _handle_ask_knowledge_base(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True,
            )
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
        )

    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        return CallToolResult(
            content=[TextContent(type="text", text=f"执行出错: {str(e)}")],
            isError=True,
        )

# ============================================================
# 入口：启动 stdio 模式的 MCP Server
# ============================================================

async def main():
    """以stdio方式启动 MCP Server"""
    logger.info("HappyTest MCP Server starting (stdio mode)...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
