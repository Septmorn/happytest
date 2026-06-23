"""
RAG服务：将文档索引、检索和生成串联起来。
"""
from dataclasses import dataclass

from openai import OpenAI

from app.service.rag_splitter import RagSplitter
from app.service.rag_vector_store import RagVectorStore

from app.core.config import settings


@dataclass
class SourceReference:
    """答案中引用的来源。"""
    source: str
    source_type: str
    chunk_index: int
    score: float


@dataclass
class RAGAnswer:
    """RAG生成的答案。"""
    text: str
    sources: list[SourceReference]
    confidence: float   # 0-1，基于检索结果的相关度


class RAGService:
    """
    RAG引擎。
    工作流：
    1. 用户提问
    2. 在向量库中检索相关片段（Retrieval）
    3. 将片段作为上下文构造 prompt（Augmentation）
    4. LLM 生成回答（Generation）
    """

    # 系统提示词：指导LLM如何基于检索结果回答
    SYSTEM_PROMPT = """你是 HappyTest 测试平台的知识助手。
请根据以下参考资料回答用户的问题。

规则：
1. 只基于提供的参考资料回答，不要编造信息
2. 如果参考资料中没有相关内容，明确告知用户
3. 回答时标注引用来源（如 [来源: xxx.md]）
4. 回答要简洁实用，直接给出可操作的建议"""

    def __init__(self, vector_store: RagVectorStore | None = None):
        self.splitter = RagSplitter()
        self.vector_store = vector_store or RagVectorStore()
        self.openai_client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )

    def ingest_file(self, file_path: str) -> int:
        """加载本地文件、切片并写入向量库"""
        chunks = self.splitter.load_and_chunk(file_path)
        return self.vector_store.add_document(chunks)

    def ingest_test_cases(self, cases: list[dict]) -> int:
        """将测试用例写入向量库。一个测试用例一个chunk。"""
        chunks = self.splitter.chunk_test_cases(cases)
        return self.vector_store.add_document(chunks)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """只做语义检索，不调用LLM。"""
        return self.vector_store.search(query, top_k=top_k)

    async def ask(self, question: str, top_k: int = 5) -> RAGAnswer:
        """
        回答用户问题。
        Args:
            question: 用户问题
            top_k: 检索的相关片段数量

        Returns:
            RAGAnswer 包含答案文本、来源引用和置信度
        """
        # Step 1：检索相关文档片段
        search_results = self.vector_store.search(question, top_k=top_k)
        if not search_results:
            return RAGAnswer(
                text="知识库中暂无相关内容，请先上传相关文档。",
                sources=[],
                confidence=0.0,
            )

        # Step 2：构造上下文
        context_parts = []
        sources = []
        for i, result in enumerate(search_results):
            source = str(result["metadata"].get("source_file") or result["metadata"].get("case_id", "unknown"))
            context_parts.append(
                f"[参考资料 {i+1}] (来源: {source})\n"
                f"{result['text']}"
            )
            sources.append(SourceReference(
                source=source,
                source_type=result["metadata"].get("source_type", "file"),
                chunk_index=result["metadata"].get("chunk_index", i),
                score=result["score"],
            ))

        context = "\n\n---\n\n".join(context_parts)

        # Step 3：调用LLM生成回答
        user_prompt = f"""参考资料：
{context}

---

用户问题：{question}

请基于上述参考资料回答。"""

        response = self.openai_client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=settings.ai_temperature,
            max_tokens=settings.ai_max_tokens,
        )

        answer_text = response.choices[0].message.content

        # 计算置信度：基于最相关结果的相似度分数
        avg_score = sum(r["score"] for r in search_results[:3]) / min(3, len(search_results))

        return RAGAnswer(
            text=answer_text,
            sources=sources,
            confidence=round(avg_score, 3),
        )
