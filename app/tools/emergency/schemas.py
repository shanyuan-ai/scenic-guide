# app/tools/emergency/schemas.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


EMERGENCY_TYPE_CHOICES = ['fire', 'crowd', 'equipment', 'weather', 'medical', 'other']
EMERGENCY_SEVERITY_CHOICES = ['low', 'medium', 'high', 'critical']
EMERGENCY_STATUS_CHOICES = ['reported', 'confirmed', 'responding', 'resolved', 'closed']


class EmergencyCreate(BaseModel):
    type: str = Field('other', description='事件类型: fire/crowd/equipment/weather/medical/other')
    severity: str = Field('medium', description='严重度: low/medium/high/critical')
    location: str = Field(..., description='事发地点/区域')
    description: str = Field(..., description='事件描述')
    affected_areas: list[str] = Field(default_factory=list, description='受影响景点区域列表')
    reporter_info: Optional[str] = Field(None, description='上报人信息')


class EmergencyUpdate(BaseModel):
    type: Optional[str] = None
    severity: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, description='状态: reported/confirmed/responding/resolved/closed')
    affected_areas: Optional[list[str]] = None
    reporter_info: Optional[str] = None


class ResponseLogCreate(BaseModel):
    action: str = Field(..., description='操作: confirm/dispatch/notify/resolve/close')
    actor: Optional[str] = Field(None, description='操作人')
    note: Optional[str] = Field(None, description='备注')


class ResponseLogResponse(BaseModel):
    id: int
    event_id: int
    action: str
    actor: Optional[str]
    note: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class EmergencyResponse(BaseModel):
    id: int
    type: str
    severity: str
    location: str
    description: str
    status: str
    affected_areas: str  # JSON 数组字符串
    reporter_info: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
