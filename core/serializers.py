# core/serializers.py

from rest_framework import serializers
from .models import NewsItem

class NewsItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsItem
        fields = [
            "id",
            "title",
            "source",
            "url",
            "summary",
            "ai_summary",
            "risk_level",
            "risk_score",
            "risk_reason",
            "priority",
            "processed_by_llm",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
