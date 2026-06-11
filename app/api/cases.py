"""
测试用例api路由，负责：
接受请求 - 参数校验 - 调用Service - 返回响应
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.schemas import CaseResponse, CaseCreateRequest, CaseUpdateRequest, HttpMethod, CaseSource
from app.dao.database import get_db
from app.dao.models import TestCase
from app.service.case_service import CaseService

router = APIRouter(prefix="/api/cases", tags=["测试用例"])

def _case_to_response(case: TestCase) -> CaseResponse:
    """将ORM对象转为相应Schema， 处理JSON字段的反序列化"""
    return CaseResponse(
        id=case.id,
        name=case.name,
        method=HttpMethod(case.method),
        url=case.url,
        headers=case.get_headers_dict(),
        body=case.get_body_dict(),
        expected_status=case.expected_status,
        assertions=case.get_assertions_list(),
        source=CaseSource(case.source),
        created_at=case.created_at,
    )

@router.post("/", response_model=CaseResponse, status_code=201)
def create_case(request: CaseCreateRequest, db: Session = Depends(get_db)):
    case = CaseService.create(db, request)
    return _case_to_response(case)

@router.get("/", response_model=list[CaseResponse])
def list_cases(
        skip: int = Query(0, ge=0, description="跳过条数"),
        limit: int = Query(default=50, ge=1, le=200, description="每页条数"),
        db: Session = Depends(get_db)
):
    """查询用例列表（分页）"""
    cases = CaseService.list_all(db, skip, limit)
    return [_case_to_response(c) for c in cases]

@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: int, db: Session = Depends(get_db)):
    """根据ID查询单个用例"""
    case = CaseService.get_by_id(db, case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"用例 {case_id} 不存在")
    return _case_to_response(case)

@router.put("/{case_id}", response_model=CaseResponse)
def update_case(case_id: int, request: CaseUpdateRequest, db: Session = Depends(get_db)):
    """更新测试用例"""
    case = CaseService.update(db, case_id, request)
    if not case:
        raise HTTPException(status_code=404, detail=f"用例 {case_id} 不存在")
    return _case_to_response(case)

@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: int, db: Session = Depends(get_db)):
    """删除测试用例"""
    success = CaseService.delete(db, case_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"用例 {case_id} 不存在")