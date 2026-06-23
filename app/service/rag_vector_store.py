"""
向量存储模块。
使用ChromaDB存储文档Embedding，支持相似度检索。
"""
import chromadb
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from chromadb.config import Settings

from app.service.rag_splitter import DocumentChunk


class RagVectorStore:
    """
    向量数据库封装层。
    1. 将文档 chunk 转换为 embedding 并存入 ChromaDB
    2. 根据查询文本进行相似度检索
    3. 管理文档的增删
    """

    def __init__(self, persist_dir: str | None = None, collection_name: str = "happytest_kb"):
        """
        Args:
            persist_dir: ChromaDB 持久化目录
            collection_name: 集合名称（类似数据库中的表）
        """
        persist_dir = persist_dir or settings.chroma_persist_dir

        # 初始化ChromaDB客户端（持久化模式）
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings()
        )

        # 获取或创建集合
        # ChromaDB 的 collection 相当于一张表，存储同一类文档的向量。
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}   # 使用余弦相似度
        )

        # sentence-transformers 本地模型，首次真正向量化时再加载，避免应用启动被模型下载阻塞。
        self.embedding_model = None

    def add_document(self, chunks: list[DocumentChunk]) -> int:
        """
        将文档片段添加到向量库。
        1. 提取所有 chunk 的文本
        2. 使用 sentence-transformers 本地模型获取向量
        3. 存入 ChromaDB（包含原文、向量、元数据）

        return:
            成功添加的chunk数量
        """
        if not chunks:
            return 0

        texts = [chunk.text for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        ids = [chunk.metadata["chunk_id"] for chunk in chunks]

        # 批量获取embedding
        embeddings = self._get_embeddings(texts)

        # 同一个文件或测试用例重复索引时，先删除旧chunk，避免chromadb id冲突
        self.collection.delete(ids=ids)

        # 存入chromadb
        self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        return len(chunks)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        语义检索：找到与查询最相似的k个文档片段。
        Returns:
            [{"text": ..., "metadata": ..., "score": ...}, ...]
        """
        # 将查询文本转换为向量
        query_embedding = self._get_embeddings([query])[0]

        # 在chromadb中检索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        # 整理结果
        search_results = []
        for i in range(len(results["ids"][0])):
            search_results.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                # chromadb 返回的是距离，转换为相似度分数。
                "score": 1 - results["distances"][0][i],
            })

        return search_results

    def delete_document(self, source_file: str) -> int:
        """删除指定来源文件的所有片段。"""
        # 查找该文件的所有 chunk ID
        results = self.collection.get(
            where={"source_file": source_file},
            include=[],
        )

        if results["ids"]:
            self.collection.delete(ids=results["ids"])

        return len(results["ids"])

    def list_documents(self) -> list[dict]:
        """列出所有已索引的文档"""
        results = self.collection.get(include=["metadatas"])

        # 按来源去重：文件按 source_file，测试用例按 case_id。
        docs = {}
        for meta in results["metadatas"]:
            if not meta:
                continue
            source_type = meta.get("source_type", "file")
            source = meta.get("source_file") or meta.get("case_id")
            if source is None:
                continue
            source_key = str(source)
            if source_key not in docs:
                docs[source_key] = {
                    "source_type": source_type,
                    "source": source_key,
                    "file_path": meta.get("file_path", ""),
                    "chunk_count": 0,
                }
            docs[source_key]["chunk_count"] += 1

        return list(docs.values())

    def _get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """使用 sentence-transformers 本地模型获取文本向量。"""
        if self.embedding_model is None:
            self.embedding_model = SentenceTransformer(settings.embedding_model)
        embeddings = self.embedding_model.encode(
            texts,
            normalize_embeddings=True,
        )
        return embeddings.tolist()
