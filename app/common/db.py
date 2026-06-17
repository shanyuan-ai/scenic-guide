# app/common/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import DB_URL

engine = create_engine(DB_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """创建所有表(如果不存在)。需在所有模型 import 之后调用。"""
    from app.common.base_model import Base
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """FastAPI 依赖注入用。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()