from rest_framework import serializers
from .models import KnowledgeItem, DigitalHumanProfile, ConversationLog, DailyStat
from django.contrib.auth.models import User

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




class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'password', 'password_confirm', 'email']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': '两次密码不一致'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(**validated_data)