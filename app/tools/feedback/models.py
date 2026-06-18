# app/tools/feedback/models.py
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean

from app.common.base_model import Base


class FeedbackItem(Base):
    __tablename__ = 'feedback_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # complaint/suggestion/praise/help
    type = Column(String(20), nullable=False, default='suggestion')
    # P1(紧急)/P2(高)/P3(中)/P4(低), 新反馈默认 P3
    priority = Column(String(5), nullable=False, default='P3')
    # 关联景点名称
    scenic_spot = Column(String(100), nullable=True)
    # 文字描述
    description = Column(Text, nullable=False)
    # JSON 数组,原子关键词标签(如 ["垃圾桶少","排队时间长"])
    # 由提交方(Agent/用户)提供,整合时据此做相似度匹配
    keywords = Column(Text, nullable=True, default='[]')
    # JSON 数组,图片相对路径(如 ["img_001.jpg", "img_002.jpg"])
    image_paths = Column(Text, nullable=True, default='[]')
    # submitted/confirmed/processing/resolved/closed/merged
    status = Column(String(20), nullable=False, default='submitted')
    # 是否已由 LLM 整合评估过(整合只处理 evaluated=False 的报单)
    evaluated = Column(Boolean, nullable=False, default=False)
    # 重复分组标识(组内最小 id); None = 未分组或单独报单
    group_id = Column(String(20), nullable=True)
    # 所属重复组的上报次数(单条=1)
    duplicate_count = Column(Integer, nullable=False, default=1)
    # LLM 为该组生成的综合摘要
    group_summary = Column(Text, nullable=True)
    # 被合并到的原始报单 id; None = 未被合并
    merged_into_id = Column(Integer, nullable=True)
    # 可选联系方式
    contact_info = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<FeedbackItem(id={self.id}, type="{self.type}", priority="{self.priority}", status="{self.status}")>'


class FeedbackRecycleBin(Base):
    """回收站:被合并/关闭的报单迁移到此表,不在主查询中出现。"""
    __tablename__ = 'feedback_recycle_bin'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 原报单 id(迁移前)
    original_id = Column(Integer, nullable=False)
    type = Column(String(20), nullable=False)
    priority = Column(String(5), nullable=False, default='P3')
    scenic_spot = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    keywords = Column(Text, nullable=True, default='[]')
    image_paths = Column(Text, nullable=True, default='[]')
    # 合并目标报单 id
    merged_into_id = Column(Integer, nullable=False)
    # 合并原因(如 "LLM判定与#3重复" 或 "相似关键词: 垃圾桶少")
    merge_reason = Column(Text, nullable=True)
    contact_info = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    archived_at = Column(DateTime, default=datetime.utcnow)
