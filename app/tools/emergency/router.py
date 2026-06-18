# app/tools/emergency/router.py
"""应急系统 REST API:事件 CRUD + 响应日志。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.common.db import get_session
from app.tools.emergency.models import EmergencyEvent, EmergencyResponseLog
from app.tools.emergency.schemas import (
    EmergencyCreate, EmergencyUpdate, EmergencyResponse,
    ResponseLogCreate, ResponseLogResponse,
)

router = APIRouter(prefix='/api/tools/emergency', tags=['应急系统'])


@router.get('/events', response_model=list[EmergencyResponse], summary='应急事件列表')
def list_events(
    skip: int = 0, limit: int = 50,
    type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    session: Session = Depends(get_session),
):
    q = session.query(EmergencyEvent).order_by(EmergencyEvent.created_at.desc())
    if type:
        q = q.filter_by(type=type)
    if severity:
        q = q.filter_by(severity=severity)
    if status:
        q = q.filter_by(status=status)
    return q.offset(skip).limit(limit).all()


@router.get('/events/{event_id}', summary='应急事件详情(含响应日志)')
def get_event(event_id: int, session: Session = Depends(get_session)):
    event = session.get(EmergencyEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail='事件不存在')
    logs = session.query(EmergencyResponseLog).filter_by(event_id=event_id).order_by(EmergencyResponseLog.created_at).all()
    return {
        'event': EmergencyResponse.model_validate(event).model_dump(),
        'response_logs': [ResponseLogResponse.model_validate(l).model_dump() for l in logs],
    }


@router.post('/events', response_model=EmergencyResponse, status_code=201, summary='上报应急事件')
def create_event(data: EmergencyCreate, session: Session = Depends(get_session)):
    event = EmergencyEvent(
        type=data.type, severity=data.severity,
        location=data.location, description=data.description,
        affected_areas=json.dumps(data.affected_areas),
        reporter_info=data.reporter_info,
        status='reported',
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.put('/events/{event_id}', response_model=EmergencyResponse, summary='更新应急事件')
def update_event(event_id: int, data: EmergencyUpdate, session: Session = Depends(get_session)):
    event = session.get(EmergencyEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail='事件不存在')
    for key, value in data.model_dump(exclude_unset=True).items():
        if key == 'affected_areas' and value is not None:
            event.affected_areas = json.dumps(value)
        else:
            setattr(event, key, value)
    session.commit()
    session.refresh(event)
    return event


@router.delete('/events/{event_id}', summary='删除应急事件')
def delete_event(event_id: int, session: Session = Depends(get_session)):
    event = session.get(EmergencyEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail='事件不存在')
    # 先删响应日志
    session.query(EmergencyResponseLog).filter_by(event_id=event_id).delete()
    session.delete(event)
    session.commit()
    return {'message': '已删除', 'id': event_id}


# ---- 响应日志 ----

@router.post('/events/{event_id}/logs', response_model=ResponseLogResponse, summary='添加响应日志')
def add_response_log(
    event_id: int, data: ResponseLogCreate, session: Session = Depends(get_session),
):
    event = session.get(EmergencyEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail='事件不存在')
    log = EmergencyResponseLog(event_id=event_id, **data.model_dump())
    session.add(log)
    # 同步更新事件状态
    if data.action == 'confirm':
        event.status = 'confirmed'
    elif data.action == 'dispatch':
        event.status = 'responding'
    elif data.action == 'resolve':
        event.status = 'resolved'
    elif data.action == 'close':
        event.status = 'closed'
    session.commit()
    session.refresh(log)
    return log


@router.get('/events/{event_id}/logs', response_model=list[ResponseLogResponse], summary='查询响应日志')
def list_response_logs(event_id: int, session: Session = Depends(get_session)):
    return session.query(EmergencyResponseLog).filter_by(event_id=event_id).order_by(EmergencyResponseLog.created_at).all()
