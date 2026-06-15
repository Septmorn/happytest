"""
MCP Server 集成测试。
使用 mcp SDK 提供的测试工具模拟客户端连接。
注意：直接运行此文件需要安装 mcp SDK：
    pip install mcp

运行测试：
    python -m pytest tests/test_mcp_server.py -v
"""

import json
import pytest
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

SERVER_PARAMS = StdioServerParameters(
    command="D:\\anaconda3\\envs\\happytest\\python.exe",
    args=["-m", "app.mcp.mcp_server"],
)


@pytest.mark.asyncio
async def test_list_tools():
    """测试工具发现：应返回 3 个工具。"""
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()

            tool_names = [t.name for t in tools.tools]
            assert "query_test_cases" in tool_names
            assert "run_test_suite" in tool_names
            assert "ask_knowledge_base" in tool_names


@pytest.mark.asyncio
async def test_query_test_cases():
    """测试查询用例工具。"""
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "query_test_cases",
                arguments={"project_name": "demo", "limit": 5},
            )

            assert not result.isError
            data = json.loads(result.content[0].text)
            assert "total" in data
            assert "cases" in data
            assert data["project"] == "demo"


@pytest.mark.asyncio
async def test_run_test_suite():
    """测试执行套件工具。"""
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "run_test_suite",
                arguments={"project_name": "demo", "base_url": "http://127.0.0.1:8080"},
            )

            assert not result.isError
            data = json.loads(result.content[0].text)
            assert "total" in data
            assert "passed" in data
            assert "failed" in data


@pytest.mark.asyncio
async def test_ask_knowledge_base():
    """测试知识库查询工具。"""
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "ask_knowledge_base",
                arguments={"question": "如何测试分页接口？"},
            )

            assert not result.isError
            data = json.loads(result.content[0].text)
            assert "answer" in data
            assert "sources" in data
            assert len(data["answer"]) > 0


@pytest.mark.asyncio
async def test_invalid_tool_returns_error():
    """测试调用不存在的工具应返回错误。"""
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "nonexistent_tool",
                arguments={},
            )
            assert result.isError
