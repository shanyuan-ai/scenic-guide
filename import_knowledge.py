import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'measurePrj.settings')
django.setup()

from docx import Document
from measureapp.models import KnowledgeItem

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


def import_from_word(filepath):
    doc = Document(filepath)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    count = 0
    for i in range(0, len(paragraphs), 2):
        title = paragraphs[i]
        content = paragraphs[i + 1] if i + 1 < len(paragraphs) else ""
        KnowledgeItem.objects.get_or_create(
            title=title,
            defaults={'content': content, 'category': 'faq', 'is_indexed': True}
        )
        count += 1
    return count


def main():
    total = 0

    if not os.path.exists(DATA_DIR):
        print(f"文件夹不存在: {DATA_DIR}")
        return

    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.docx'):
            filepath = os.path.join(DATA_DIR, filename)
            count = import_from_word(filepath)
            print(f"[Word] {filename} → 导入 {count} 条")
            total += count

    print(f"\n全部完成，共导入 {total} 条记录")


if __name__ == '__main__':
    main()
