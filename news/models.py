# news/models.py
from django.db import models

class Article(models.Model):
    title = models.CharField(max_length=500)
    url = models.URLField(unique=True)
    content = models.TextField()
    summary = models.TextField(null=True, blank=True)
    authors = models.TextField(null=True, blank=True)
    publish_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ArticleEmbedding(models.Model):
    article = models.OneToOneField(Article, on_delete=models.CASCADE)
    vector = models.BinaryField()  # store FAISS vector raw bytes
