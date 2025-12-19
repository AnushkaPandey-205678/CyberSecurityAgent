from django.db import models


class NewsItem(models.Model):
  
    source = models.CharField(max_length=255)
    url = models.URLField(max_length=500, blank=True, null=True)
    title = models.CharField(max_length=500)
    summary = models.TextField()  # Short excerpt from scraping
    content = models.TextField(blank=True)  # Full article content
    ai_summary = models.TextField(null=True, blank=True)  # Your 500+ word summary
    url = models.TextField(null=True, blank=True)
    priority = models.IntegerField(default=1)
    # Add these fields for content tracking
    content_length = models.IntegerField(default=0)
    summary_length = models.IntegerField(default=0)
    word_count = models.IntegerField(default=0)
    reading_time_minutes = models.IntegerField(default=0)
    # ---- LLM PROCESSING FIELDS -----
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
    risk_score = models.IntegerField(default=5)  # 1 to 10
    risk_reason = models.TextField(null=True, blank=True)

    processed_by_llm = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    priority = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title[:100]


