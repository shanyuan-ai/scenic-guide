from rest_framework import serializers
from .models import KnowledgeItem, DigitalHumanProfile, ConversationLog, DailyStat

class KnowledgeItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeItem
        fields = '__all__'


class DigitalHumanProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DigitalHumanProfile
        fields = '__all__'


class ConversationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationLog
        fields = '__all__'


class DailyStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyStat
        fields = '__all__'
