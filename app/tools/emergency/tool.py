# app/tools/emergency/tool.py
"""应急系统工具:上报、追踪、更新应急事件。"""
import json
from typing import Any

from app.tools.base import ToolBase
from app.tools.emergency.router import router as emergency_router
from app.common.db import SessionLocal
from app.tools.emergency.models import EmergencyEvent, EmergencyResponseLog


class EmergencyTool(ToolBase):
    name = 'emergency'
    description = '上报和管理景区应急事件(火灾/拥挤/设备故障/天气/医疗等),追踪响应流程'

    @property
    def input_schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'action': {
                    'type': 'string',
                    'enum': ['report', 'list', 'update', 'add_log'],
                    'description': '操作: report=上报事件, list=查询事件, update=更新状态, add_log=添加响应日志',
                },
                'type': {
                    'type': 'string',
                    'enum': ['fire', 'crowd', 'equipment', 'weather', 'medical', 'other'],
                    'description': '事件类型',
                },
                'severity': {
                    'type': 'string',
                    'enum': ['low', 'medium', 'high', 'critical'],
                    'description': '严重度',
                },
                'location': {'type': 'string', 'description': '事发地点(report 时必填)'},
                'description': {'type': 'string', 'description': '事件描述(report 时必填)'},
                'affected_areas': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': '受影响景点区域列表',
                },
                'event_id': {'type': 'integer', 'description': '事件 ID(update/add_log 时必填)'},
                'status': {'type': 'string', 'description': '新状态(update 时必填)'},
                'log_action': {'type': 'string', 'description': '日志操作类型(add_log 时必填): confirm/dispatch/notify/resolve/close'},
                'note': {'type': 'string', 'description': '日志备注'},
                'actor': {'type': 'string', 'description': '操作人'},
            },
            'required': ['action'],
        }

    async def execute(self, params: dict) -> Any:
        action = params.get('action', 'list')
        session = SessionLocal()

        try:
            if action == 'report':
                event = EmergencyEvent(
                    type=params.get('type', 'other'),
                    severity=params.get('severity', 'medium'),
                    location=params.get('location', ''),
                    description=params.get('description', ''),
                    affected_areas=json.dumps(params.get('affected_areas', [])),
                    reporter_info=params.get('actor'),
                    status='reported',
                )
                session.add(event)
                session.commit()
                session.refresh(event)
                return {'id': event.id, 'type': event.type, 'severity': event.severity, 'status': event.status, 'location': event.location}

            elif action == 'list':
                q = session.query(EmergencyEvent).order_by(EmergencyEvent.created_at.desc())
                if params.get('type'):
                    q = q.filter_by(type=params['type'])
                if params.get('severity'):
                    q = q.filter_by(severity=params['severity'])
                if params.get('status'):
                    q = q.filter_by(status=params['status'])
                items = q.limit(20).all()
                return [{
                    'id': e.id, 'type': e.type, 'severity': e.severity,
                    'location': e.location, 'status': e.status,
                    'description': e.description[:60],
                    'affected_areas': json.loads(e.affected_areas or '[]'),
                } for e in items]

            elif action == 'update':
                event_id = params.get('event_id')
                if not event_id:
                    return {'error': 'event_id 必填'}
                event = session.get(EmergencyEvent, event_id)
                if not event:
                    return {'error': '事件不存在'}
                if params.get('status'):
                    event.status = params['status']
                if params.get('severity'):
                    event.severity = params['severity']
                if params.get('affected_areas'):
                    event.affected_areas = json.dumps(params['affected_areas'])
                session.commit()
                return {'id': event.id, 'status': event.status}

            elif action == 'add_log':
                event_id = params.get('event_id')
                if not event_id:
                    return {'error': 'event_id 必填'}
                event = session.get(EmergencyEvent, event_id)
                if not event:
                    return {'error': '事件不存在'}
                log = EmergencyResponseLog(
                    event_id=event_id,
                    action=params.get('log_action', 'confirm'),
                    actor=params.get('actor'),
                    note=params.get('note'),
                )
                session.add(log)
                # 自动更新事件状态
                log_action = params.get('log_action', 'confirm')
                if log_action == 'confirm' and event.status == 'reported':
                    event.status = 'confirmed'
                elif log_action == 'dispatch':
                    event.status = 'responding'
                elif log_action == 'resolve':
                    event.status = 'resolved'
                elif log_action == 'close':
                    event.status = 'closed'
                session.commit()
                return {'event_id': event_id, 'log_action': log_action, 'event_status': event.status}

            else:
                return {'error': f'未知 action: {action}'}
        finally:
            session.close()

    def get_router(self):
        return emergency_router
