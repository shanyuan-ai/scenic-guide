# app/tools/feedback/schemas.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


FEEDBACK_TYPE_CHOICES = ['complaint', 'suggestion', 'praise', 'help']
SEVERITY_CHOICES = ['low', 'medium', 'high', 'critical']
FEEDBACK_STATUS_CHOICES = ['submitted', 'confirmed', 'processing', 'resolved', 'closed']


class FeedbackCreate(BaseModel):
    type: str = Field('suggestion', description='反馈类型: complaint/suggestion/praise/help')
    severity: str = Field('medium', description='严重度: low/medium/high/critical')
    scenic_spot: Optional[str] = Field(None, description='关联景点名称')
    description: str = Field(..., description='文字描述')
    contact_info: Optional[str] = Field(None, description='联系方式(可选)')


class FeedbackUpdate(BaseModel):
    type: Optional[str] = None
    severity: Optional[str] = None
    scenic_spot: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, description='状态: submitted/confirmed/processing/resolved/closed')
    contact_info: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    type: str
    severity: str
    scenic_spot: Optional[str]
    description: str
    image_paths: str  # JSON 数组字符串
    status: str
    contact_info: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
