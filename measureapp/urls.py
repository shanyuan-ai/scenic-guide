from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from .views import ChatView, DashboardView, KnowledgeItemViewSet,WordUploadView
from .auth_views import RegisterView, LoginView, LogoutView, UserInfoView, RefreshTokenView

router = DefaultRouter()
router.register(r'knowledge', KnowledgeItemViewSet, basename='knowledge')

urlpatterns = [
    # 页面
    path('login-page/', TemplateView.as_view(template_name='login.html'), name='login_page'),
    path('chat-page/', TemplateView.as_view(template_name='chat.html'), name='chat_page'),

    # 认证
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('user-info/', UserInfoView.as_view(), name='user_info'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh'),

    # 业务
    path('chat/', ChatView.as_view(), name='chat'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('', include(router.urls)),
    path('upload-word/', WordUploadView.as_view(), name='upload_word'),
]