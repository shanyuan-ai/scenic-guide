from django.contrib import admin
from .models import KnowledgeItem

@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'created_at']