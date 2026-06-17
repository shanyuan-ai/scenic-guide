# app/tools/feedback/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

from app.common.base_model import Base


class FeedbackItem(Base):
    __tablename__ = 'feedback_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # complaint/suggestion/praise/help
    type = Column(String(20), nullable=False, default='suggestion')
    # low/medium/high/critical
    severity = Column(String(20), nullable=False, default='medium')
    # 关联景点名称
    scenic_spot = Column(String(100), nullable=True)
    # 文字描述
    description = Column(Text, nullable=False)
    # JSON 数组,图片相对路径(如 ["img_001.jpg", "img_002.jpg"])
    image_paths = Column(Text, nullable=True, default='[]')
    # submitted/confirmed/processing/resolved/closed
    status = Column(String(20), nullable=False, default='submitted')
    # 可选联系方式
    contact_info = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<FeedbackItem(id={self.id}, type="{self.type}", status="{self.status}")>'
