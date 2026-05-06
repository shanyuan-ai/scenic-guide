from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, status
from django.db.models import Count, Avg
from django.utils import timezone

from .models import KnowledgeItem, ConversationLog
from .serializers import KnowledgeItemSerializer
from .llm_utils import call_doubao

from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import WordUploadForm
from .word_importer import parse_word_file
import os
from django.conf import settings

class KnowledgeItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = KnowledgeItem.objects.all().order_by('-created_at')
    serializer_class = KnowledgeItemSerializer

class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_input = request.data.get('message', '')
        session_id = request.data.get('session_id', '')

        if not user_input:
            return Response({
                'code': 400,
                'data': None,
                'message': '消息内容不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        from django.db.models import Q

        matched_items = KnowledgeItem.objects.filter(
            Q(title__icontains=user_input) | Q(content__icontains=user_input)
        )[:5]
        context = '\n'.join([item.content for item in matched_items])
        print("=== 检索到的上下文 ===")
        print(context)
        print("=== 上下文结束 ===")
        ai_answer = call_doubao(user_input, context=context)


        ConversationLog.objects.create(
            session_id=session_id,
            user_input=user_input,
            ai_response=ai_answer,
            sentiment_score=0.8
        )

        return Response({
            'code': 200,
            'data': {
                'response_text': ai_answer,
                'emotion': 'smile',
                'action': 'explain',
            },
            'message': 'success'
        })



class DashboardView(APIView):

    permission_classes = [IsAuthenticated]
    def get(self, request):
        today = timezone.now().date()

        today_logs = ConversationLog.objects.filter(created_at__date=today)
        today_visitors = today_logs.values('session_id').distinct().count()
        total_conversations = today_logs.count()
        avg_result = today_logs.aggregate(avg=Avg('sentiment_score'))
        avg_sentiment = round(avg_result['avg'] or 0, 2)

        hot_questions = ['门票价格', '开放时间', '最佳游览路线']

        return Response({
            'code': 200,
            'data': {
                'today_visitors': today_visitors,
                'total_conversations': total_conversations,
                'avg_sentiment': avg_sentiment,
                'hot_questions': hot_questions,
            },
            'message': 'success'
        })

class WordUploadView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        form = WordUploadForm()
        return render(request, 'admin/upload_word.html', {'form': form})

    def post(self, request):

        token = request.query_params.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')

        if not token:
            return Response({
                'code': 401,
                'message': '身份认证信息未提供。'
            }, status=status.HTTP_401_UNAUTHORIZED)

        try:
            from rest_framework_simplejwt.tokens import AccessToken
            AccessToken(token)
        except Exception:
            return Response({
                'code': 401,
                'message': 'Token 无效或已过期。'
            }, status=status.HTTP_401_UNAUTHORIZED)

        form = WordUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            temp_dir = os.path.join(settings.BASE_DIR, 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            temp_path = os.path.join(temp_dir, uploaded_file.name)

            with open(temp_path, 'wb+') as dest:
                for chunk in uploaded_file.chunks():
                    dest.write(chunk)

            count = parse_word_file(temp_path)
            os.remove(temp_path)

            return Response({
                'code': 200,
                'message': f'导入成功，共 {count} 条记录'
            })

        return Response({
            'code': 400,
            'message': '文件上传失败'
        }, status=status.HTTP_400_BAD_REQUEST)