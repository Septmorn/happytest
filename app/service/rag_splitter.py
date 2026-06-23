"""
文档加载和切片模块
"""
import re
from dataclasses import dataclass
from pathlib import Path

import json


@dataclass
class DocumentChunk:
    """一个文档片段"""
    text: str           # 片段文本内容
    metadata: dict      # 元数据：来源文件、片段索引等
    chunk_index: int    # 在原文档中的位置


class RagSplitter:
    """
    文档切片器。
    - 对测试用例不做字符切分、不做 overlap，避免破坏请求/断言/预期结果的完整性。
    - 普通 Markdown/TXT 文档仍按段落组合成 chunk，用于测试规范、最佳实践等资料。
    """
    def __init__(self, chunk_size: int = 750):
        self.chunk_size = chunk_size

    def chunk_test_cases(self, cases: list[dict]) -> list[DocumentChunk]:
        """将测试用例转换为chunks。一个测试用例一个chunk，不重叠"""
        chunks = []
        for i, case in enumerate(cases):
            case_id = str(case.get("id", i))
            chunks.append(
                DocumentChunk(
                    text=self._format_test_case(case),
                    metadata={
                        "chunk_id": f"test_case:{case_id}",
                        "source_type": "test_case",
                        "case_id": case_id,
                        "name": case.get("name", ""),
                        "method": case.get("method", ""),
                        "url": case.get("url", ""),
                        "category": case.get("category", ""),
                        "source": case.get("source", ""),
                        "priority": case.get("priority", ""),
                        "chunk_index": i,
                    },
                    chunk_index=i,
                )
            )
        return chunks

    def load_and_chunk(self, file_path: str) -> list[DocumentChunk]:
        """加载文件并切片。支持.md和.txt格式。"""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"文件不存在：{file_path}")

        if path.suffix not in (".md", ".txt"):
            raise ValueError(f"不支持的文件格式：{path.suffix}，仅支持.md和.txt")

        text = path.read_text(encoding="utf-8")
        chunks = self._split_text(text)

        return [
            DocumentChunk(
                text=chunk_text,
                metadata={
                    "chunk_id": f"file:{path.name}:{i}",
                    "source_type": "file",
                    "source_file": path.name,
                    "file_path": str(path),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
                chunk_index=i,
            )
            for i, chunk_text in enumerate(chunks)
        ]

    def _split_text(self, text: str) -> list[str]:
        """
        把普通文档切分成chunks。
        策略：
        1. 先按段落（双换行）分割
        2. 将段落组合成不超过 chunk_size 的块
        3. 普通文档保留完整段落，不在测试用例切片中使用
        """
        # 按段落分割（两个及以上换行符）
        paragraphs = re.split(r"\n{2,}", text.strip())
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # 如果当前段落加进来后不超限，就继续拼接。
            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk = current_chunk + "\n\n" + para if current_chunk else para
            else:
                # 当前chunk已满，保存并开始新chunk
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = para
                else:
                    # 单个段落就超过chunk_size，强制切割
                    for i in range(0, len(para), self.chunk_size):
                        chunks.append(para[i : i + self.chunk_size])
                    current_chunk = ""

        # 保存最后一个chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    @staticmethod
    def _format_test_case(case: dict) -> str:
        """把结构化测试用例格式化为适合embedding的可读文本"""
        return "\n".join(
            [
                f"用例名称：{case.get('name', '')}",
                f"请求方法: {case.get('method', '')}",
                f"接口路径: {case.get('url', '')}",
                f"场景分类: {case.get('category', '')}",
                f"用例描述: {case.get('description', '')}",
                f"请求头: {json.dumps(case.get('headers') or {}, ensure_ascii=False)}",
                f"请求体: {json.dumps(case.get('body') or {}, ensure_ascii=False)}",
                f"预期状态码: {case.get('expected_status', '')}",
                f"断言: {json.dumps(case.get('assertions') or [], ensure_ascii=False)}",
            ]
        )
