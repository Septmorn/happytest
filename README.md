# HappyTest

AI 驱动的接口测试平台，集成 LLM 智能用例生成、自动化执行与结果分析。

## 技术栈

- Python 3.11 / FastAPI
- DeepSeek (OpenAI SDK) / LLM Function Calling
- ChromaDB (RAG 知识库)
- pytest (自动化执行)
- MCP Protocol
- Docker

## 功能概览

- 接口信息管理（CRUD）
- AI 自动生成测试用例（基于 LLM Function Calling）
- 测试用例自动执行与结果分析
- MCP Server 集成，支持 AI 客户端直接调用测试工具
- RAG 知识库，支持历史用例检索与上下文增强

---

# HappyTest (English)

An AI-driven API testing platform with LLM-powered test case generation, automated execution, and result analysis.

## Tech Stack

- Python 3.11 / FastAPI
- DeepSeek (OpenAI SDK) / LLM Function Calling
- ChromaDB (RAG knowledge base)
- pytest (automated execution)
- MCP Protocol
- Docker

## Features

- API management (CRUD)
- AI-powered test case generation via LLM Function Calling
- Automated test execution and result analysis
- MCP Server integration for AI client access
- RAG knowledge base for historical case retrieval and context augmentation
