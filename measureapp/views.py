# measureapp/views.py
import hashlib
import time
import os

from django.core.cache import cache
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.shortcuts import render
from django.conf import settings

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, status

from .models import KnowledgeItem, ConversationLog
from .serializers import KnowledgeItemSerializer
from .llm_utils import call_ai_model
from .vector_service import vector_service
from .utils.sentiment import analyze_sentiment
from .forms import WordUploadForm
from .word_importer import parse_word_file


class KnowledgeItemViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = KnowledgeItem.objects.all().order_by('-created_at')
    serializer_class = KnowledgeItemSerializer


class ChatView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user_input = request.data.get('message', '')
        session_id = request.data.get('session_id', '')

        if not user_input:
            return Response({
                'code': 400,
                'message': '消息内容不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        cache_key = f"ai_answer_{hashlib.md5(user_input.encode()).hexdigest()}"
        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response)

        retrieved_docs = vector_service.search(user_input, top_k=5)
        context = '\n\n'.join([f"【{d['title']}】\n{d['content']}" for d in retrieved_docs]) if retrieved_docs else "暂无相关知识"

        ai_answer = call_ai_model(user_input, context=context)
        sentiment_score = analyze_sentiment(user_input)

        ConversationLog.objects.create(
            session_id=session_id,
            user_input=user_input,
            ai_response=ai_answer,
            sentiment_score=sentiment_score
        )

        emotion = 'smile' if sentiment_score >= 0.7 else ('neutral' if sentiment_score >= 0.4 else 'sad')

        response_data = {
            'code': 200,
            'data': {
                'response_text': ai_answer,
                'emotion': emotion,
                'action': 'explain',
                'used_knowledge': len(retrieved_docs),
            },
            'message': 'success'
        }

        cache.set(cache_key, response_data, timeout=1800)
        return Response(response_data)


class DashboardView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        today = timezone.now().date()
        today_logs = ConversationLog.objects.filter(created_at__date=today)
        week_ago = timezone.now() - timezone.timedelta(days=7)

        return Response({
            'code': 200,
            'data': {
                'today_visitors': today_logs.values('session_id').distinct().count(),
                'total_conversations': today_logs.count(),
                'avg_sentiment': round(today_logs.aggregate(avg=Avg('sentiment_score'))['avg'] or 0, 2),
                'hot_questions': [
                    item['user_input'][:30]
                    for item in ConversationLog.objects.filter(created_at__gte=week_ago)
                    .values('user_input').annotate(count=Count('id'))
                    .order_by('-count')[:5] if item['user_input']
                ] or ['门票价格', '开放时间', '最佳游览路线'],
            },
            'message': 'success'
        })


class WordUploadView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return render(request, 'admin/upload_word.html', {'form': WordUploadForm()})

    def post(self, request):
        form = WordUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return Response({'code': 400, 'message': '文件上传失败'}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES['file']
        temp_path = os.path.join(settings.BASE_DIR, 'temp', uploaded_file.name)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)

        with open(temp_path, 'wb+') as dest:
            for chunk in uploaded_file.chunks():
                dest.write(chunk)

        count = parse_word_file(temp_path)
        os.remove(temp_path)

        if count > 0:
            vector_service.sync_all_knowledge()

        return Response({'code': 200, 'message': f'导入成功，共 {count} 条记录'})