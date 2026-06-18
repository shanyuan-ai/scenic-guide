# app/tools/feedback/schemas.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


FEEDBACK_TYPE_CHOICES = ['complaint', 'suggestion', 'praise', 'help']
PRIORITY_CHOICES = ['P1', 'P2', 'P3', 'P4']
FEEDBACK_STATUS_CHOICES = ['submitted', 'confirmed', 'processing', 'resolved', 'closed', 'merged']


class FeedbackCreate(BaseModel):
    type: str = Field('suggestion', description='反馈类型: complaint/suggestion/praise/help')
    priority: str = Field('P3', description='优先级: P1(紧急)/P2(高)/P3(中)/P4(低)')
    scenic_spot: Optional[str] = Field(None, description='关联景点名称')
    description: str = Field(..., description='文字描述')
    keywords: Optional[list[str]] = Field(None, description='关键词标签(原子化,如 ["垃圾桶少","排队时间长"])')
    contact_info: Optional[str] = Field(None, description='联系方式(可选)')


class FeedbackUpdate(BaseModel):
    type: Optional[str] = None
    priority: Optional[str] = Field(None, description='优先级: P1/P2/P3/P4')
    scenic_spot: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[list[str]] = None
    status: Optional[str] = Field(None, description='状态: submitted/confirmed/processing/resolved/closed')
    contact_info: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    type: str
    priority: str
    scenic_spot: Optional[str]
    description: str
    keywords: str  # JSON 数组字符串
    image_paths: str  # JSON 数组字符串
    status: str
    evaluated: bool
    group_id: Optional[str]
    duplicate_count: int
    group_summary: Optional[str]
    merged_into_id: Optional[int]
    contact_info: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RecycleBinResponse(BaseModel):
    id: int
    original_id: int
    type: str
    priority: str
    scenic_spot: Optional[str]
    description: str
    keywords: str
    merged_into_id: int
    merge_reason: Optional[str]
    contact_info: Optional[str]
    created_at: Optional[datetime]
    archived_at: Optional[datetime]

    class Config:
        from_attributes = True


class IntegrateResult(BaseModel):
    """整合执行结果统计。"""
    evaluated_count: int = Field(0, description='本次评估的报单数')
    merged_count: int = Field(0, description='被合并(移入回收站)的报单数')
    new_groups: int = Field(0, description='新形成的分组数')
    priority_upgrades: int = Field(0, description='优先级被提升的报单数')
    method: str = Field('llm', description='整合方式: llm(模型) 或 rule(规则降级)')
    error: Optional[str] = Field(None, description='LLM 不可用时返回的错误信息')
