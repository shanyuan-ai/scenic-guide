# measureapp/views.py
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, status
from django.db.models import Count, Avg
from django.utils import timezone
from django.db.models import Q

from .models import KnowledgeItem, ConversationLog
from .serializers import KnowledgeItemSerializer
from .llm_utils import call_ai_model
from .vector_service import vector_service
from .utils.sentiment import analyze_sentiment

from django.shortcuts import render
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
        model_type = request.data.get('model_type', 'doubao')

        if not user_input:
            return Response({
                'code': 400,
                'data': None,
                'message': '消息内容不能为空'
            }, status=status.HTTP_400_BAD_REQUEST)


        retrieved_docs = vector_service.search(user_input, top_k=5)


        context_parts = []
        sources = []
        if retrieved_docs:
            for doc in retrieved_docs:
                context_parts.append(f"【{doc['title']}】\n{doc['content']}")
                sources.append({
                    'title': doc['title'],
                    'category': doc.get('category', 'knowledge'),
                    'score': doc.get('score', 0),
                    'type': doc.get('source_type', 'vector')
                })
            context = '\n\n'.join(context_parts)

            print(f"=== 向量检索到 {len(retrieved_docs)} 条知识 ===")
            for doc in retrieved_docs:
                source_type = doc.get('source_type', 'vector')
                print(f"  - {doc['title']} (相似度: {doc['score']:.2f}, 来源: {source_type})")
        else:
            context = "暂无相关知识"
            print("=== 向量检索未找到相关知识 ===")


        ai_answer = call_ai_model(user_input, context=context, model_type=model_type)

        sentiment_score = analyze_sentiment(user_input)

        ConversationLog.objects.create(
            session_id=session_id,
            user_input=user_input,
            ai_response=ai_answer,
            sentiment_score=sentiment_score
        )

        if sentiment_score >= 0.7:
            emotion = 'smile'
        elif sentiment_score >= 0.4:
            emotion = 'neutral'
        else:
            emotion = 'sad'

        return Response({
            'code': 200,
            'data': {
                'response_text': ai_answer,
                'emotion': emotion,
                'action': 'explain',
                'used_knowledge': len(retrieved_docs),
                'model_used': model_type,
                'sources': sources  # 新增：告诉前端答案来源
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


        week_ago = timezone.now() - timezone.timedelta(days=7)
        hot_questions_data = ConversationLog.objects.filter(
            created_at__gte=week_ago
        ).values('user_input').annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        hot_questions = [item['user_input'][:30] for item in hot_questions_data if item['user_input']]

        if not hot_questions:
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
        # JWT 验证
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

            if count > 0:
                try:
                    # 重新同步所有知识到向量库（确保最新）
                    synced_count = vector_service.sync_all_knowledge()
                    print(f"Word 导入完成，已同步 {synced_count} 条知识到向量库")
                except Exception as e:
                    print(f"同步向量库失败: {e}")
                    # 即使同步失败，也返回导入成功，只是提示用户
                    return Response({
                        'code': 200,
                        'message': f'导入成功，共 {count} 条记录，但向量库同步失败，请手动运行同步命令'
                    })

            return Response({
                'code': 200,
                'message': f'导入成功，共 {count} 条记录，已同步到向量库'
            })

        return Response({
            'code': 400,
            'message': '文件上传失败'
        }, status=status.HTTP_400_BAD_REQUEST)