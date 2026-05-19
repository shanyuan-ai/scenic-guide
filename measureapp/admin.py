from django.contrib import admin
from .models import KnowledgeItem

@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_indexed', 'created_at']
    list_filter = ['category', 'is_indexed']
    search_fields = ['title', 'content']
