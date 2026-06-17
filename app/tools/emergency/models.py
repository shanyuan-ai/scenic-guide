# app/tools/emergency/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.common.base_model import Base


class EmergencyEvent(Base):
    __tablename__ = 'emergency_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # fire/crowd/equipment/weather/medical/other
    type = Column(String(20), nullable=False, default='other')
    # low/medium/high/critical
    severity = Column(String(20), nullable=False, default='medium')
    # 事发地点/区域
    location = Column(String(100), nullable=False)
    # 事件描述
    description = Column(Text, nullable=False)
    # reported/confirmed/responding/resolved/closed
    status = Column(String(20), nullable=False, default='reported')
    # JSON 数组,受影响景点区域(如 ["灵山大佛","梵宫"])
    affected_areas = Column(Text, nullable=True, default='[]')
    # 上报人信息
    reporter_info = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    response_logs = relationship('EmergencyResponseLog', back_populates='event', order_by='EmergencyResponseLog.created_at')

    def __repr__(self):
        return f'<EmergencyEvent(id={self.id}, type="{self.type}", severity="{self.severity}", status="{self.status}")>'


class EmergencyResponseLog(Base):
    __tablename__ = 'emergency_response_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey('emergency_events.id'), nullable=False)
    # confirm/dispatch/notify/resolve/close 等
    action = Column(String(20), nullable=False)
    # 操作人
    actor = Column(String(100), nullable=True)
    # 备注
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship('EmergencyEvent', back_populates='response_logs')

    def __repr__(self):
        return f'<ResponseLog(id={self.id}, action="{self.action}")>'
