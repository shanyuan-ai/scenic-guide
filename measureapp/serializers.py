from rest_framework import serializers
from .models import KnowledgeItem, ConversationLog


class KnowledgeItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeItem
        fields = '__all__'


class ConversationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationLog
        fields = '__all__'