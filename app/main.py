"""
FastAPI应用入口，创建应用实例、注册路由、启动时初始化数据库
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.cases import router as cases_router
from app.api.routes.ai_routes import router as ai_router
from app.dao.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    startup：创建数据库表（如果不存在）。
    shutdown：清理资源。
    """
    # === Startup ===
    # 根据 ORM 模型自动创建表（表已存在则跳过）
    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified.")
    yield
    # === Shutdown ===
    print("Application shutting down.")

app = FastAPI(
    title="HappyTest",
    description="AI 驱动的 API 自动化测试平台",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(cases_router)
app.include_router(ai_router)

@app.get("/health", tags=["系统"])
def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "happytest"}
