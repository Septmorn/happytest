"""
MCP Server 单元测试。

这里直接测试 MCP 工具定义与分发逻辑，避免启动真实 stdio 子进程，
也避免在默认测试中触发数据库、pytest 执行器、embedding 模型或外部 LLM。
"""

import json

import pytest

from app.mcp import mcp_server


@pytest.mark.asyncio
async def test_list_tools():
    """测试工具发现：应返回 3 个工具。"""
    tools = await mcp_server.list_tools()

    tool_names = [t.name for t in tools]
    assert "query_test_cases" in tool_names
    assert "run_test_suite" in tool_names
    assert "ask_knowledge_base" in tool_names


@pytest.mark.asyncio
async def test_query_test_cases(monkeypatch):
    """测试查询用例工具的 MCP 分发。"""

    async def fake_handle(args):
        return {
            "total": 0,
            "project": args["project_name"],
            "filters": {"status": "all", "source": "all"},
            "cases": [],
        }

    monkeypatch.setattr(mcp_server, "_handle_query_test_cases", fake_handle)

    result = await mcp_server.call_tool(
        "query_test_cases",
        arguments={"project_name": "demo", "limit": 5},
    )

    assert not result.isError
    data = json.loads(result.content[0].text)
    assert data["total"] == 0
    assert data["cases"] == []
    assert data["project"] == "demo"


@pytest.mark.asyncio
async def test_run_test_suite(monkeypatch):
    """测试执行套件工具的 MCP 分发。"""

    async def fake_handle(args):
        return {
            "total": 1,
            "passed": 1,
            "failed": 0,
            "error": 0,
            "duration_seconds": 0.01,
            "failures": [],
        }

    monkeypatch.setattr(mcp_server, "_handle_run_test_suite", fake_handle)

    result = await mcp_server.call_tool(
        "run_test_suite",
        arguments={"project_name": "demo", "base_url": "http://127.0.0.1:8080"},
    )

    assert not result.isError
    data = json.loads(result.content[0].text)
    assert data["total"] == 1
    assert data["passed"] == 1
    assert data["failed"] == 0


@pytest.mark.asyncio
async def test_ask_knowledge_base(monkeypatch):
    """测试知识库查询工具的 MCP 分发。"""

    async def fake_handle(args):
        return {
            "question": args["question"],
            "answer": "分页接口需要覆盖页码边界、页大小边界和非法参数。",
            "sources": [],
            "confidence": 0.0,
        }

    monkeypatch.setattr(mcp_server, "_handle_ask_knowledge_base", fake_handle)

    result = await mcp_server.call_tool(
        "ask_knowledge_base",
        arguments={"question": "如何测试分页接口？"},
    )

    assert not result.isError
    data = json.loads(result.content[0].text)
    assert data["question"] == "如何测试分页接口？"
    assert "answer" in data
    assert "sources" in data
    assert len(data["answer"]) > 0


@pytest.mark.asyncio
async def test_invalid_tool_returns_error():
    """测试调用不存在的工具应返回错误。"""
    result = await mcp_server.call_tool(
        "nonexistent_tool",
        arguments={},
    )

    assert result.isError
