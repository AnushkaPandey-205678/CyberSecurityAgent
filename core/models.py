from django.db import models

class NewsItem(models.Model):
    title = models.CharField(max_length=255)
    summary = models.TextField()
    content = models.TextField(blank=True)
    source = models.CharField(max_length=255)
    url = models.URLField(max_length=500, blank=True, null=True)   # <-- ADD THIS
    priority = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
