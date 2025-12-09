from django.db import models


class NewsItem(models.Model):
    title = models.CharField(max_length=255)
    summary = models.TextField()  # original extracted summary
    content = models.TextField(blank=True)
    source = models.CharField(max_length=255)
    url = models.URLField(max_length=500, blank=True, null=True)

    # ---- LLM PROCESSING FIELDS -----
    ai_summary = models.TextField(null=True, blank=True)
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='low'
    )
    risk_score = models.IntegerField(default=1)  # 1 to 10
    risk_reason = models.TextField(null=True, blank=True)

    processed_by_llm = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    priority = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


