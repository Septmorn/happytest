"""
RAG 知识库 API 路由。
提供文档上传、查询、管理等接口。
"""
import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dao.database import get_db
from app.service.case_service import CaseService
from app.service.rag_service import RAGService

router = APIRouter(prefix="/api/rag", tags=["RAG"])

# 初始化依赖
rag_service = RAGService()

# 上传文件的临时存储路径
UPLOAD_DIR = Path("./data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ──────── 请求/响应模型 ────────
class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


class AskResponse(BaseModel):
    answer: str
    sources: list[dict]
    confidence: float


class DocumentInfo(BaseModel):
    source_type: str
    source: str
    file_path: str
    chunk_count: int


class UploadResponse(BaseModel):
    filename: str
    chunks_created: int
    message: str


class IngestCasesResponse(BaseModel):
    cases_indexed: int
    message: str

# ──────── 路由实现 ────────

@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    上传文档到知识库。
    支持 .md 和 .txt 格式。文件会被切片、embedding、存入向量数据库。
    """
    # 验证文件格式
    filename = Path(file.filename or "").name
    if not filename.endswith((".md", ".txt")):
        raise HTTPException(
            status_code=400,
            detail="仅支持 .md 和 .txt 格式的文件",
        )

    # 保存上传文件
    file_path = UPLOAD_DIR / filename
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        count = rag_service.ingest_file(str(file_path))
        return UploadResponse(
            filename=filename,
            chunks_created=count,
            message=f"文档已成功索引，共生成 {count} 个知识片段",
        )
    except Exception as e:
        # 清理已保存的文件
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"处理文档失败：{str(e)}")


@router.post("/ingest-cases", response_model=IngestCasesResponse)
async def ingest_test_cases(db: Session = Depends(get_db)):
    """把数据库中的测试用例写入知识库。一个测试用例一个chunk"""
    cases = CaseService.list_all(db=db, skip=0, limit=1000)
    case_dicts = [
        {
            "id": case.id,
            "name": case.name,
            "method": case.method,
            "url": case.url,
            "headers": case.get_headers_dict() or {},
            "body": case.get_body_dict() or {},
            "expected_status": case.expected_status,
            "assertions": case.get_assertions_list() or [],
            "source": case.source,
            "category": case.category or "",
            "description": case.description or "",
            "priority": case.priority or "",
        }
        for case in cases
    ]
    count = rag_service.ingest_test_cases(case_dicts)
    return IngestCasesResponse(
        cases_indexed=count,
        message=f"已索引 {count} 条测试用例",
    )


@router.post("/query")
async def query_document(request: QueryRequest):
    """只检索相关文档片段，不调用LLM。"""
    if not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail="查询内容不能为空"
        )

    return {
        "query": request.query,
        "result": rag_service.search(request.query, request.top_k),
    }


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    向知识库提问
    使用 RAG 模式：检索相关片段 + LLM 生成回答。
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    answer = await rag_service.ask(request.question, request.top_k)

    return AskResponse(
        answer=answer.text,
        sources=[
            {
                "source": s.source,
                "source_type": s.source_type,
                "chunk_index": s.chunk_index,
                "relevance_score": s.score,
            }
            for s in answer.sources
        ],
        confidence=answer.confidence,
    )


@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents():
    """列出所有已索引的文档。"""
    return rag_service.vector_store.list_documents()


@router.delete("/documents/{filename}")
async def delete_document(filename: str):
    """
    从知识库中删除指定文档的所有片段。
    同时删除上传的原始文件。
    """
    filename = Path(filename).name
    deleted_count = rag_service.vector_store.delete_document(filename)

    if deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"未找到文档: {filename}")

    # 删除原始文件
    file_path = UPLOAD_DIR / filename
    file_path.unlink(missing_ok=True)

    return {
        "filename": filename,
        "deleted_chunks": deleted_count,
        "message": f"已删除文档 {filename} 的 {deleted_count} 个知识片段",
    }
