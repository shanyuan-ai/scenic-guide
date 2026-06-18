# app/common/db.py
import logging

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session

from app.config import DB_URL

logger = logging.getLogger(__name__)

engine = create_engine(DB_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """创建所有表(如果不存在)。需在所有模型 import 之后调用。"""
    from app.common.base_model import Base
    Base.metadata.create_all(bind=engine)


def migrate_feedback_table():
    """检测 feedback_items 表是否有旧 severity 列(无 priority 列),
    若有则 drop 旧表并重建(数据为空,无损失)。

    同时确保 FeedbackRecycleBin 表存在。
    """
    from app.common.base_model import Base
    inspector = inspect(engine)

    # 确保 recycle_bin 表存在
    if 'feedback_recycle_bin' not in inspector.get_table_names():
        RecycleBin = Base.metadata.tables.get('feedback_recycle_bin')
        if RecycleBin is not None:
            Base.metadata.create_all(bind=engine, tables=[RecycleBin])
            logger.info('feedback_recycle_bin 表已创建')

    if 'feedback_items' not in inspector.get_table_names():
        # 表不存在,create_all 会创建
        return

    columns = {col['name'] for col in inspector.get_columns('feedback_items')}
    need_rebuild = ('severity' in columns and 'priority' not in columns) or \
                   ('priority' in columns and 'keywords' not in columns)

    if need_rebuild:
        logger.info('检测到 feedback_items 旧结构或缺列,重建为新结构')
        FeedbackItemTbl = Base.metadata.tables.get('feedback_items')
        if FeedbackItemTbl is not None:
            FeedbackItemTbl.drop(bind=engine)
            logger.info('旧 feedback_items 表已删除')
            Base.metadata.create_all(bind=engine, tables=[FeedbackItemTbl])
            logger.info('新 feedback_items 表已创建')


def get_session() -> Session:
    """FastAPI 依赖注入用。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()