# app/tools/rag/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime

from app.common.base_model import Base, CATEGORY_MAP


class KnowledgeItem(Base):
    __tablename__ = 'measureapp_knowledgeitem'  # 兼容旧 db.sqlite3

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)
    category = Column(String(20), nullable=False)
    is_indexed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def category_display(self):
        return CATEGORY_MAP.get(self.category, self.category)

    def __repr__(self):
        return f'<KnowledgeItem(id={self.id}, title="{self.title}")>'
