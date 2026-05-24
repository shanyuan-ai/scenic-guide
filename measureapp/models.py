from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


class KnowledgeItem(models.Model):
    CATEGORY_CHOICES = [
        ('history', '历史典故'),
        ('nature', '自然风光'),
        ('faq', '常见问题'),
        ('route', '路线推荐'),
    ]
    title = models.CharField(max_length=200, verbose_name='标题', db_index=True)
    content = models.TextField(verbose_name='内容')
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        verbose_name='分类'
    )
    embedding_vector = models.TextField(
        blank=True,
        null=True,
        verbose_name='向量字段(预留)'
    )
    is_indexed = models.BooleanField(
        default=False,
        verbose_name='是否入索引'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '知识库条目'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


class DigitalHumanProfile(models.Model):
    name = models.CharField(max_length=50, verbose_name='形象名称')
    avatar_url = models.URLField(verbose_name='形象地址')
    voice_id = models.CharField(max_length=50, verbose_name='音色ID')
    welcome_text = models.TextField(verbose_name='欢迎语')

    class Meta:
        verbose_name = '数字人形象'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class ConversationLog(models.Model):
    session_id = models.CharField(max_length=100, verbose_name='会话ID')
    user_input = models.TextField(verbose_name='用户输入')
    ai_response = models.TextField(verbose_name='AI回复')
    sentiment_score = models.FloatField(default=0.0, verbose_name='情感分数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '对话记录'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.session_id} - {self.created_at}'


class DailyStat(models.Model):
    date = models.DateField(unique=True, verbose_name='日期')
    visitor_count = models.IntegerField(default=0, verbose_name='服务人次')
    avg_sentiment = models.FloatField(default=0.0, verbose_name='平均满意度')
    top_question = models.JSONField(default=list, verbose_name='热门问答')

    class Meta:
        verbose_name = '每日统计'
        verbose_name_plural = verbose_name

    def __str__(self):
        return str(self.date)


@receiver(post_save, sender=KnowledgeItem)
def sync_knowledge_on_save(sender, instance, created, **kwargs):
    """保存知识条目时自动同步到检索索引"""
    from .vector_service import vector_service
    vector_service.add_knowledge_item(instance)


@receiver(post_delete, sender=KnowledgeItem)
def delete_knowledge_on_delete(sender, instance, **kwargs):
    """删除知识条目时自动同步到检索索引"""
    from .vector_service import vector_service
    vector_service.delete_knowledge_item(instance)