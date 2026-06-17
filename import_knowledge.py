"""Word 文档(.docx)知识导入脚本(FastAPI/SQLAlchemy 版)。

读取 data/ 目录下的 .docx 文件,按"标题/正文"交替的段落结构导入知识库。
导入后自动重建向量索引。

用法:
    python import_knowledge.py [可选 .docx 文件路径]
"""
import os
import sys

from docx import Document

from app.common.db import init_db, SessionLocal
from app.tools.rag.models import KnowledgeItem
from app.tools.rag.vector_service import vector_service

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def import_from_word(filepath, default_category='faq'):
    doc = Document(filepath)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    session = SessionLocal()
    count = 0
    try:
        for i in range(0, len(paragraphs), 2):
            title = paragraphs[i]
            content = paragraphs[i + 1] if i + 1 < len(paragraphs) else ''

            existing = session.query(KnowledgeItem).filter_by(title=title).first()
            if existing:
                existing.content = content
                existing.category = default_category
                existing.is_indexed = True
            else:
                session.add(KnowledgeItem(
                    title=title,
                    content=content,
                    category=default_category,
                    is_indexed=True,
                ))
            count += 1
        session.commit()
    finally:
        session.close()
    return count


def main():
    init_db()

    # 支持命令行指定单个文件,否则扫描 data/ 目录
    if len(sys.argv) > 1:
        files = [sys.argv[1]]
    elif os.path.isdir(DATA_DIR):
        files = [
            os.path.join(DATA_DIR, f)
            for f in os.listdir(DATA_DIR)
            if f.endswith('.docx')
        ]
    else:
        files = []

    if not files:
        print(f'未找到 .docx 文件,data 目录: {DATA_DIR}')
        print('用法: python import_knowledge.py [文件路径]')
        return

    total = 0
    for filepath in files:
        if not os.path.exists(filepath):
            print(f'[跳过] 文件不存在: {filepath}')
            continue
        count = import_from_word(filepath)
        print(f'[Word] {os.path.basename(filepath)} → 导入 {count} 条')
        total += count

    indexed = vector_service.sync_all_knowledge()
    print(f'\n全部完成，共导入 {total} 条记录，索引 {indexed} 条文档')


if __name__ == '__main__':
    main()
