from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from .views import (
    ChatView,
    DashboardView,
    KnowledgeItemViewSet,
    WordUploadView,
)

router = DefaultRouter()
router.register(r'knowledge', KnowledgeItemViewSet, basename='knowledge')

urlpatterns = [
    path('chat-page/', TemplateView.as_view(template_name='chat.html'), name='chat_page'),

    path('chat/', ChatView.as_view(), name='chat'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('', include(router.urls)),
    path('upload-word/', WordUploadView.as_view(), name='upload_word'),
]