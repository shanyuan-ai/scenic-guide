# app/tools/feedback/router.py
"""用户反馈 REST API: CRUD + 图片上传 + 智能整合端点 + 回收站。"""
import json
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.common.db import get_session
from app.tools.feedback.models import FeedbackItem, FeedbackRecycleBin
from app.tools.feedback.schemas import (
    FeedbackCreate, FeedbackUpdate, FeedbackResponse,
    RecycleBinResponse, IntegrateResult,
    FEEDBACK_TYPE_CHOICES, PRIORITY_CHOICES, FEEDBACK_STATUS_CHOICES,
)
from app.tools.feedback.integrator import integrate_feedback

router = APIRouter(prefix='/api/tools/feedback', tags=['用户反馈'])

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _run_integration():
    """后台整合任务(用于 BackgroundTasks)。"""
    from app.common.db import SessionLocal
    session = SessionLocal()
    try:
        integrate_feedback(session)
    finally:
        session.close()


@router.get('', response_model=list[FeedbackResponse], summary='反馈列表')
def list_feedback(
    skip: int = 0, limit: int = 50,
    type: str | None = None,
    priority: str | None = None,
    status: str | None = None,
    scenic_spot: str | None = None,
    session: Session = Depends(get_session),
):
    """列出反馈(自动排除已合并的,即 status='merged' 不出现在列表中)。"""
    q = session.query(FeedbackItem).order_by(FeedbackItem.created_at.desc())
    # 默认排除 merged 状态
    if status and status != 'merged':
        q = q.filter(FeedbackItem.status != 'merged').filter_by(status=status)
    elif not status:
        q = q.filter(FeedbackItem.status != 'merged')
    # 如果明确查 merged,也允许(但一般用回收站端点)
    if type:
        q = q.filter_by(type=type)
    if priority:
        q = q.filter_by(priority=priority)
    if scenic_spot:
        q = q.filter_by(scenic_spot=scenic_spot)
    return q.offset(skip).limit(limit).all()


# ---- 静态路由必须在 /{item_id} 之前声明 ----
# FastAPI 按声明顺序匹配,若 /{item_id} 在前,/recycle-bin 会被当成 item_id
# 解析为 int 而抛 422。所有不含路径参数的静态端点都放在动态端点之前。

@router.post('/integrate', response_model=IntegrateResult, summary='手动触发智能整合')
def manual_integrate(session: Session = Depends(get_session)):
    """管理员/外部调度器手动触发报单智能整合(LLM 分组+合并+摘要)。"""
    return integrate_feedback(session)


@router.get('/recycle-bin', response_model=list[RecycleBinResponse], summary='回收站列表')
def list_recycle_bin(
    skip: int = 0, limit: int = 50,
    session: Session = Depends(get_session),
):
    """查看被合并/关闭的报单(回收站)。"""
    return session.query(FeedbackRecycleBin).order_by(
        FeedbackRecycleBin.archived_at.desc()
    ).offset(skip).limit(limit).all()


@router.get('/{item_id}', response_model=FeedbackResponse, summary='反馈详情')
def get_feedback(item_id: int, session: Session = Depends(get_session)):
    item = session.get(FeedbackItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail='反馈不存在')
    return item


@router.post('', response_model=FeedbackResponse, status_code=201, summary='提交反馈')
def create_feedback(
    data: FeedbackCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """提交反馈后自动触发后台智能整合。"""
    item = FeedbackItem(
        type=data.type,
        priority=data.priority,
        scenic_spot=data.scenic_spot,
        description=data.description,
        keywords=json.dumps(data.keywords or []),
        image_paths='[]',
        contact_info=data.contact_info,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    # 后台触发整合
    background_tasks.add_task(_run_integration)
    return item


@router.put('/{item_id}', response_model=FeedbackResponse, summary='更新反馈')
def update_feedback(
    item_id: int, data: FeedbackUpdate, session: Session = Depends(get_session),
):
    item = session.get(FeedbackItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail='反馈不存在')
    for key, value in data.model_dump(exclude_unset=True).items():
        if key == 'keywords' and value is not None:
            setattr(item, key, json.dumps(value))
        else:
            setattr(item, key, value)
    session.commit()
    session.refresh(item)
    return item


@router.delete('/{item_id}', summary='删除反馈')
def delete_feedback(item_id: int, session: Session = Depends(get_session)):
    item = session.get(FeedbackItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail='反馈不存在')
    # 清理关联图片
    paths = json.loads(item.image_paths or '[]')
    for p in paths:
        fp = UPLOAD_DIR / p
        if fp.exists():
            fp.unlink()
    session.delete(item)
    session.commit()
    return {'message': '已删除', 'id': item_id}


@router.post('/{item_id}/images', summary='上传反馈图片')
def upload_images(
    item_id: int,
    files: list[UploadFile] = File(...),
    session: Session = Depends(get_session),
):
    item = session.get(FeedbackItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail='反馈不存在')

    existing = json.loads(item.image_paths or '[]')
    for f in files:
        ext = os.path.splitext(f.filename or 'img.jpg')[1]
        filename = f'feedback_{item_id}_{uuid.uuid4().hex[:8]}{ext}'
        dest = UPLOAD_DIR / filename
        with open(dest, 'wb') as out:
            content = f.file.read()
            out.write(content)
        existing.append(filename)

    item.image_paths = json.dumps(existing)
    session.commit()
    return {'uploaded': len(files), 'image_paths': existing}
