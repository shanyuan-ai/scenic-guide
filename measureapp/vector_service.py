# measureapp/vector_service.py
import jieba
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import KnowledgeItem


class VectorService:
    def __init__(self):
        print("正在初始化景区专用向量检索系统...")

        # 景区专有实体词库
        self.scenic_entities = {
            '景点': ['灵山大佛', '九龙灌浴', '梵宫', '五印坛城', '祥符禅寺', '佛手广场', '曼飞龙塔', '灵山精舍'],
            '活动': ['抱佛脚', '摸佛掌', '撞钟', '转经筒', '祈福'],
            '文化': ['佛教', '禅意', '藏传佛教', '汉传佛教', '五方五佛'],
            '实用': ['门票', '开放时间', '路线', '素斋', '住宿']
        }

        # 高频问题缓存（精确匹配）
        self.hot_questions_cache = {
            "门票": "灵山胜境门票参考价格为210元/人（具体以景区公告为准），包含灵山大佛、九龙灌浴、梵宫等主要景点。",
            "门票多少钱": "灵山胜境门票参考价格为210元/人，学生、老人等优惠政策请咨询景区。",
            "开放时间": "灵山胜境开放时间为每天7:30-17:30（旺季可能延长，建议提前查询）。",
            "几点开门": "灵山胜境开放时间为每天7:30-17:30。",
            "怎么去": "可乘坐公交88路、89路直达灵山胜境，或自驾导航'灵山胜境停车场'。"
        }

        self.vectorizer = None
        self.documents = []
        self.vectors = None
        self.knowledge_items = []
        self.sync_all_knowledge()

    def _tokenize(self, text):
        """中文分词 + 实体识别增强"""
        words = jieba.cut(text)
        result = []
        for word in words:
            result.append(word)
            # 如果分词结果是景区实体，添加权重标记
            for category, entities in self.scenic_entities.items():
                if word in entities:
                    result.extend([word, word])  # 重复两次增加权重
        return ' '.join(result)

    def extract_entities(self, query):
        """提取问题中的景区实体"""
        found_entities = {}
        for category, entities in self.scenic_entities.items():
            for entity in entities:
                if entity in query:
                    if category not in found_entities:
                        found_entities[category] = []
                    found_entities[category].append(entity)
        return found_entities

    def check_hot_question(self, query):
        """检查是否是高频问题（精确匹配）"""
        for key, answer in self.hot_questions_cache.items():
            if key in query:
                return answer
        return None

    def sync_all_knowledge(self):
        """同步所有知识库到向量索引"""
        print("正在构建景区知识索引...")
        self.knowledge_items = list(KnowledgeItem.objects.all())
        if not self.knowledge_items:
            print("⚠️ 知识库为空，跳过索引")
            return

        self.documents = []
        for item in self.knowledge_items:
            # 为标题中的实体增加权重
            text = f"{item.title}\n{item.content}"
            self.documents.append(self._tokenize(text))

        self.vectorizer = TfidfVectorizer()
        self.vectors = self.vectorizer.fit_transform(self.documents)
        print(f"✅ 索引完成！共 {len(self.documents)} 条知识")

    def search(self, query, top_k=5):
        """多路召回检索"""
        # 第一路：高频问题缓存
        cached_answer = self.check_hot_question(query)
        if cached_answer:
            return [{
                'content': cached_answer,
                'title': '高频问题缓存',
                'category': 'hot_question',
                'score': 1.0,
                'source_type': 'cache'
            }]

        # 第二路：实体识别增强
        entities = self.extract_entities(query)
        entity_hint = ""
        for category, entity_list in entities.items():
            entity_hint += f" {' '.join(entity_list)} " * 2

        # 合并原始查询和实体增强
        enhanced_query = query + " " + entity_hint

        if not self.documents or self.vectors is None:
            return []

        # 分词处理
        query_tokens = self._tokenize(enhanced_query)
        query_vec = self.vectorizer.transform([query_tokens])

        # 计算相似度
        similarities = cosine_similarity(query_vec, self.vectors)[0]

        # 获取 top_k 个结果
        results = []
        indexed_similarities = list(enumerate(similarities))
        indexed_similarities.sort(key=lambda x: x[1], reverse=True)

        # 第三路：如果向量检索结果不好，补充关键词匹配
        need_keyword_fallback = indexed_similarities[0][1] < 0.2 if indexed_similarities else True

        for idx, score in indexed_similarities[:top_k]:
            if score > 0.05:  # 降低阈值，让更多结果有机会
                item = self.knowledge_items[idx]
                result = {
                    'content': item.content,
                    'title': item.title,
                    'category': item.category,
                    'score': float(score),
                    'source_type': 'vector'
                }
                results.append(result)

        # 如果向量检索结果不理想，进行关键词补充
        if need_keyword_fallback and len(results) < 3:
            keyword_results = self._keyword_search(query)
            for kr in keyword_results:
                if kr not in results:
                    results.append(kr)
                    if len(results) >= top_k:
                        break

        return results

    def _keyword_search(self, query):
        """关键词检索作为兜底"""
        results = []
        keywords = jieba.lcut(query)
        for item in self.knowledge_items:
            score = 0
            text = f"{item.title} {item.content}"
            for kw in keywords:
                if kw in text and len(kw) > 1:
                    score += text.count(kw)
            if score > 0:
                results.append({
                    'content': item.content,
                    'title': item.title,
                    'category': item.category,
                    'score': min(score / 10, 0.5),
                    'source_type': 'keyword'
                })
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:3]


vector_service = VectorService()