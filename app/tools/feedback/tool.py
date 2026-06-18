# app/tools/feedback/tool.py
"""用户反馈工具:提交、查询、更新游客反馈。"""
import json
from typing import Any

from app.tools.base import ToolBase
from app.tools.feedback.router import router as feedback_router
from app.common.db import SessionLocal
from app.tools.feedback.models import FeedbackItem
from app.tools.feedback.integrator import integrate_feedback


class FeedbackTool(ToolBase):
    name = 'feedback'
    description = '提交、查询、更新游客反馈(投诉/建议/表扬/求助),支持按类型/优先级/状态筛选'

    @property
    def input_schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'action': {
                    'type': 'string',
                    'enum': ['create', 'list', 'update_status', 'integrate'],
                    'description': '操作: create=提交反馈, list=查询列表, update_status=更新状态, integrate=触发智能整合',
                },
                'type': {
                    'type': 'string',
                    'enum': ['complaint', 'suggestion', 'praise', 'help'],
                    'description': '反馈类型',
                },
                'priority': {
                    'type': 'string',
                    'enum': ['P1', 'P2', 'P3', 'P4'],
                    'description': '优先级: P1(紧急)/P2(高)/P3(中)/P4(低)',
                },
                'scenic_spot': {'type': 'string', 'description': '关联景点'},
                'description': {'type': 'string', 'description': '文字描述(create 时必填)'},
                'keywords': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': '关键词标签(如 ["垃圾桶少","排队时间长"])',
                },
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
            if action == 'integrate':
                result = integrate_feedback(session)
                return result

            if action == 'create':
                item = FeedbackItem(
                    type=params.get('type', 'suggestion'),
                    priority=params.get('priority', 'P3'),
                    scenic_spot=params.get('scenic_spot'),
                    description=params.get('description', ''),
                    keywords=json.dumps(params.get('keywords', [])),
                    contact_info=params.get('contact_info'),
                    image_paths='[]',
                )
                session.add(item)
                session.commit()
                session.refresh(item)
                # 创建后触发整合
                integrate_feedback(session)
                return {
                    'id': item.id, 'type': item.type,
                    'priority': item.priority, 'status': item.status,
                    'keywords': json.loads(item.keywords or '[]'),
                }

            elif action == 'list':
                q = session.query(FeedbackItem).filter(
                    FeedbackItem.status != 'merged'
                ).order_by(FeedbackItem.created_at.desc())
                if params.get('type'):
                    q = q.filter_by(type=params['type'])
                if params.get('priority'):
                    q = q.filter_by(priority=params['priority'])
                if params.get('status'):
                    q = q.filter_by(status=params['status'])
                items = q.limit(20).all()
                return [{
                    'id': i.id, 'type': i.type, 'priority': i.priority,
                    'scenic_spot': i.scenic_spot, 'status': i.status,
                    'keywords': json.loads(i.keywords or '[]'),
                    'evaluated': i.evaluated,
                    'group_id': i.group_id,
                    'duplicate_count': i.duplicate_count,
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
