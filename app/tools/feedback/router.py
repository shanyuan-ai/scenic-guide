# app/tools/feedback/router.py
"""用户反馈 REST API:CRUD + 图片上传。"""
import json
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.common.db import get_session
from app.tools.feedback.models import FeedbackItem
from app.tools.feedback.schemas import (
    FeedbackCreate, FeedbackUpdate, FeedbackResponse,
    FEEDBACK_TYPE_CHOICES, SEVERITY_CHOICES, FEEDBACK_STATUS_CHOICES,
)

router = APIRouter(prefix='/api/tools/feedback', tags=['用户反馈'])

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get('', response_model=list[FeedbackResponse], summary='反馈列表')
def list_feedback(
    skip: int = 0, limit: int = 50,
    type: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    scenic_spot: str | None = None,
    session: Session = Depends(get_session),
):
    q = session.query(FeedbackItem).order_by(FeedbackItem.created_at.desc())
    if type:
        q = q.filter_by(type=type)
    if severity:
        q = q.filter_by(severity=severity)
    if status:
        q = q.filter_by(status=status)
    if scenic_spot:
        q = q.filter_by(scenic_spot=scenic_spot)
    return q.offset(skip).limit(limit).all()


@router.get('/{item_id}', response_model=FeedbackResponse, summary='反馈详情')
def get_feedback(item_id: int, session: Session = Depends(get_session)):
    item = session.get(FeedbackItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail='反馈不存在')
    return item


@router.post('', response_model=FeedbackResponse, status_code=201, summary='提交反馈')
def create_feedback(data: FeedbackCreate, session: Session = Depends(get_session)):
    item = FeedbackItem(**data.model_dump(), image_paths='[]')
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.put('/{item_id}', response_model=FeedbackResponse, summary='更新反馈')
def update_feedback(
    item_id: int, data: FeedbackUpdate, session: Session = Depends(get_session),
):
    item = session.get(FeedbackItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail='反馈不存在')
    for key, value in data.model_dump(exclude_unset=True).items():
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
