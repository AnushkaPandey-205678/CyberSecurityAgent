# news/models.py
from django.db import models

class Article(models.Model):
    title = models.CharField(max_length=500)
    url = models.URLField(unique=True)
    content = models.TextField()

    # original scraped summary
    summary = models.TextField(null=True, blank=True)

    # ---- LLM fields ----
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
    risk_score = models.IntegerField(default=1)
    risk_reason = models.TextField(null=True, blank=True)

    processed_by_llm = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    authors = models.TextField(null=True, blank=True)
    publish_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class ArticleEmbedding(models.Model):
    article = models.OneToOneField(Article, on_delete=models.CASCADE)
    vector = models.BinaryField()  # store FAISS vector
