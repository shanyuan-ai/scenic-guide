from django.urls import path, include
from django.views.generic import TemplateView, RedirectView
from rest_framework.routers import DefaultRouter
from .views import (
    ChatView,
    DashboardView,
    KnowledgeItemViewSet,
    WordUploadView,
    RagIndexStatusView,
    RagSearchView,
    RagReindexView,
    RagSetIndexedView,
)

router = DefaultRouter()
router.register(r'knowledge', KnowledgeItemViewSet, basename='knowledge')

urlpatterns = [
    # 页面
    path('', RedirectView.as_view(url='/api/rag-admin-page/', permanent=False), name='api_home'),
    path('chat-page/', TemplateView.as_view(template_name='chat.html'), name='chat_page'),
    path('rag-admin-page/', TemplateView.as_view(template_name='rag_admin.html'), name='rag_admin_page'),

    # 业务
    path('chat/', ChatView.as_view(), name='chat'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('rag/index-status/', RagIndexStatusView.as_view(), name='rag_index_status'),
    path('rag/search/', RagSearchView.as_view(), name='rag_search'),
    path('rag/reindex/', RagReindexView.as_view(), name='rag_reindex'),
    path('rag/set-indexed/', RagSetIndexedView.as_view(), name='rag_set_indexed'),
    path('', include(router.urls)),
    path('upload-word/', WordUploadView.as_view(), name='upload_word'),
]
