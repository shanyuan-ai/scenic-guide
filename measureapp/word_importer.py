from docx import Document
from .models import KnowledgeItem


# measureapp/word_importer.py
def parse_word_file(file_path, default_category='faq'):
    doc = Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    count = 0

    # 修复：从 0 开始，0,2,4... 是标题
    for i in range(0, len(paragraphs), 2):
        title = paragraphs[i]
        content = paragraphs[i + 1] if i + 1 < len(paragraphs) else ''

        item, created = KnowledgeItem.objects.get_or_create(
            title=title,
            defaults={
                'content': content,
                'category': default_category,
                'is_indexed': True,
            }
        )
        if not created:
            # Keep existing is_indexed state; only refresh content/category.
            item.content = content
            item.category = default_category
            item.save(update_fields=['content', 'category'])
        count += 1

    return count
