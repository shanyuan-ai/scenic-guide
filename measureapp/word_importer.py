from docx import Document
from .models import KnowledgeItem


def parse_word_file(file_path, default_category='faq'):
    doc = Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    count = 0

    for i in range(1, len(paragraphs), 2):
        title = paragraphs[i]
        content = paragraphs[i + 1] if i + 1 < len(paragraphs) else ''

        KnowledgeItem.objects.update_or_create(
            title=title,
            defaults={
                'content': content,
                'category': default_category
            }
        )
        count += 1

    return count