"""
数据库连接和会话管理。
"""
import pymysql
pymysql.connections.SSL_ENABLED = False

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    echo=True if settings.app_env == "development" else False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()