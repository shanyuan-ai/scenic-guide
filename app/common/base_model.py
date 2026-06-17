# app/common/base_model.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# 景区知识分类映射(原 app/models.py)
CATEGORY_MAP = {
    'history': '历史典故',
    'nature': '自然风光',
    'faq': '常见问题',
    'route': '路线推荐',
}