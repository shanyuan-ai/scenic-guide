# measureapp/views.py
import hashlib
import time
import os

from django.core.cache import cache
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.shortcuts import render
from django.conf import settings

from rest_framework.permissions import IsAuthenticated, AllowAny
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


# ==================== 知识库 CRUD ====================
class KnowledgeItemViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = KnowledgeItem.objects.all().order_by('-created_at')
    serializer_class = KnowledgeItemSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        is_indexed = self.request.query_params.get('is_indexed')
        if is_indexed is not None:
            if str(is_indexed).lower() in {'1', 'true', 'yes', 'on'}:
                qs = qs.filter(is_indexed=True)
            elif str(is_indexed).lower() in {'0', 'false', 'no', 'off'}:
                qs = qs.filter(is_indexed=False)

        q = (self.request.query_params.get('q') or '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))

        category = (self.request.query_params.get('category') or '').strip()
        if category:
            qs = qs.filter(category=category)
        return qs


# ==================== RAG 索引状态管理（师哥的功能） ====================
class RagIndexStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        total = KnowledgeItem.objects.count()
        indexed = KnowledgeItem.objects.filter(is_indexed=True).count()
        unindexed = total - indexed

        category_counts = list(
            KnowledgeItem.objects.values('category').annotate(count=Count('id')).order_by('-count')
        )
        indexed_category_counts = list(
            KnowledgeItem.objects.filter(is_indexed=True).values('category').annotate(count=Count('id')).order_by('-count')
        )
        unindexed_category_counts = list(
            KnowledgeItem.objects.filter(is_indexed=False).values('category').annotate(count=Count('id')).order_by('-count')
        )

        return Response({
            'code': 200,
            'data': {
                'total': total,
                'indexed': indexed,
                'unindexed': unindexed,
                'vector_index': {
                    'index_ready': getattr(vector_service, '_index_ready', False),
                    'dirty': getattr(vector_service, '_dirty', False),
                    'indexed_doc_count': len(getattr(vector_service, 'documents', []) or []),
                    'indexed_db_count': indexed,
                    'embeddings_ready': getattr(vector_service, 'embeddings', None) is not None,
                    'model_error': getattr(vector_service, 'model_error', None),
                },
                'category_counts': category_counts,
                'indexed_category_counts': indexed_category_counts,
                'unindexed_category_counts': unindexed_category_counts,
            },
            'message': 'success'
        })


class RagSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = (request.query_params.get('query') or '').strip()
        top_k = int(request.query_params.get('top_k') or 5)
        if not query:
            return Response({'code': 400, 'message': 'query 不能为空', 'data': None}, status=status.HTTP_400_BAD_REQUEST)

        results = vector_service.search(query, top_k=top_k)
        return Response({'code': 200, 'data': results, 'message': 'success'})


class RagReindexView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        count = vector_service.sync_all_knowledge()
        return Response({'code': 200, 'data': {'indexed_doc_count': count}, 'message': 'success'})


class RagSetIndexedView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ids = request.data.get('ids') or []
        is_indexed = request.data.get('is_indexed')

        if not isinstance(ids, list) or not ids:
            return Response({'code': 400, 'message': 'ids 必须是非空数组', 'data': None}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(is_indexed, bool):
            return Response({'code': 400, 'message': 'is_indexed 必须是布尔值', 'data': None}, status=status.HTTP_400_BAD_REQUEST)

        updated = KnowledgeItem.objects.filter(id__in=ids).update(is_indexed=is_indexed)
        indexed_doc_count = vector_service.sync_all_knowledge()
        return Response({
            'code': 200,
            'data': {
                'updated': updated,
                'indexed_doc_count': indexed_doc_count,
            },
            'message': 'success'
        })


# ==================== 游客对话接口（你的缓存功能） ====================
class ChatView(APIView):
    permission_classes = [AllowAny]

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

        # ==================== 缓存查询 ====================
        cache_key = f"ai_answer_{hashlib.md5(user_input.encode()).hexdigest()}"
        cached_response = cache.get(cache_key)

        if cached_response:
            print(f"=== 缓存命中，直接返回 ===")
            return Response(cached_response)

        # ==================== 向量检索 ====================
        start_search = time.time()
        try:
            retrieved_docs = vector_service.search(user_input, top_k=5)
        except Exception as e:
            print(f"向量检索异常: {e}")
            retrieved_docs = []
        search_time = time.time() - start_search
        print(f"检索耗时: {search_time:.3f} 秒")

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

        # ==================== 调用大模型 ====================
        start_llm = time.time()
        try:
            ai_answer = call_ai_model(user_input, context=context, model_type=model_type)
        except Exception as e:
            print(f"AI 模型调用异常: {e}")
            ai_answer = "抱歉，AI 服务暂时繁忙，请稍后再试。"
        llm_time = time.time() - start_llm
        print(f"豆包大模型耗时: {llm_time:.3f} 秒")

        # ==================== 情感分析 ====================
        sentiment_score = analyze_sentiment(user_input)

        # ==================== 保存对话记录 ====================
        try:
            ConversationLog.objects.create(
                session_id=session_id,
                user_input=user_input,
                ai_response=ai_answer,
                sentiment_score=sentiment_score
            )
        except Exception as e:
            print(f"对话日志写入异常: {e}")

        # ==================== 根据情感得分选择表情 ====================
        if sentiment_score >= 0.7:
            emotion = 'smile'
        elif sentiment_score >= 0.4:
            emotion = 'neutral'
        else:
            emotion = 'sad'

        # ==================== 构建响应并缓存 ====================
        response_data = {
            'code': 200,
            'data': {
                'response_text': ai_answer,
                'emotion': emotion,
                'action': 'explain',
                'used_knowledge': len(retrieved_docs),
                'model_used': model_type,
                'sources': sources
            },
            'message': 'success'
        }

        # 缓存 30 分钟
        try:
            cache.set(cache_key, response_data, timeout=1800)
        except Exception as e:
            print(f"缓存写入失败: {e}")

        return Response(response_data)


# ==================== 数据大屏接口 ====================
class DashboardView(APIView):
    permission_classes = [AllowAny]

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


# ==================== Word 上传导入接口 ====================
class WordUploadView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        form = WordUploadForm()
        return render(request, 'admin/upload_word.html', {'form': form})

    def post(self, request):
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
                    synced_count = vector_service.sync_all_knowledge()
                    print(f"Word 导入完成，已同步 {synced_count} 条知识到向量库")
                except Exception as e:
                    print(f"同步向量库失败: {e}")
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