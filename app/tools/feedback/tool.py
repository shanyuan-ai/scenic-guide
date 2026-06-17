# app/tools/feedback/tool.py
"""用户反馈工具:提交、查询、追踪游客反馈。"""
from typing import Any

from app.tools.base import ToolBase
from app.tools.feedback.router import router as feedback_router
from app.common.db import SessionLocal
from app.tools.feedback.models import FeedbackItem


class FeedbackTool(ToolBase):
    name = 'feedback'
    description = '提交、查询、更新游客反馈(投诉/建议/表扬/求助),支持按类型/严重度/状态筛选'

    @property
    def input_schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'action': {
                    'type': 'string',
                    'enum': ['create', 'list', 'update_status'],
                    'description': '操作: create=提交反馈, list=查询列表, update_status=更新状态',
                },
                'type': {
                    'type': 'string',
                    'enum': ['complaint', 'suggestion', 'praise', 'help'],
                    'description': '反馈类型',
                },
                'severity': {
                    'type': 'string',
                    'enum': ['low', 'medium', 'high', 'critical'],
                    'description': '严重度',
                },
                'scenic_spot': {'type': 'string', 'description': '关联景点'},
                'description': {'type': 'string', 'description': '文字描述(create 时必填)'},
                'contact_info': {'type': 'string', 'description': '联系方式(可选)'},
                'status': {'type': 'string', 'description': '状态(update_status 时必填)'},
                'item_id': {'type': 'integer', 'description': '反馈 ID(update_status 时必填)'},
            },
            'required': ['action'],
        }

    async def execute(self, params: dict) -> Any:
        action = params.get('action', 'list')
        session = SessionLocal()

        try:
            if action == 'create':
                item = FeedbackItem(
                    type=params.get('type', 'suggestion'),
                    severity=params.get('severity', 'medium'),
                    scenic_spot=params.get('scenic_spot'),
                    description=params.get('description', ''),
                    contact_info=params.get('contact_info'),
                    image_paths='[]',
                )
                session.add(item)
                session.commit()
                session.refresh(item)
                return {'id': item.id, 'type': item.type, 'status': item.status}

            elif action == 'list':
                q = session.query(FeedbackItem).order_by(FeedbackItem.created_at.desc())
                if params.get('type'):
                    q = q.filter_by(type=params['type'])
                if params.get('severity'):
                    q = q.filter_by(severity=params['severity'])
                if params.get('status'):
                    q = q.filter_by(status=params['status'])
                items = q.limit(20).all()
                return [{
                    'id': i.id, 'type': i.type, 'severity': i.severity,
                    'scenic_spot': i.scenic_spot, 'status': i.status,
                    'description': i.description[:60],
                } for i in items]

            elif action == 'update_status':
                item_id = params.get('item_id')
                if not item_id:
                    return {'error': 'item_id 必填'}
                item = session.get(FeedbackItem, item_id)
                if not item:
                    return {'error': '反馈不存在'}
                item.status = params.get('status', item.status)
                session.commit()
                return {'id': item.id, 'status': item.status}

            else:
                return {'error': f'未知 action: {action}'}
        finally:
            session.close()

    def get_router(self):
        return feedback_router
