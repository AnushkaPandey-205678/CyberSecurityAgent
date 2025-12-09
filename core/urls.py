# core/urls.py

from django.urls import path
from .views import (
    ProcessedNewsListAPIView,
    NewsDetailAPIView,
    clean_old_news,
    delete_all_news,
    run_scraper_view,
    AllNewsListAPIView,
    process_news_api,
    reprocess_news_api,
    processing_stats_api,
)

urlpatterns = [
    # Existing URLs
    path('news/processed/', ProcessedNewsListAPIView.as_view(), name='processed-news-list'),
    path('news/<int:id>/', NewsDetailAPIView.as_view(), name='news-detail'),
    path('scrape/', run_scraper_view, name='run-scraper'),
    path('news/all/', AllNewsListAPIView.as_view(), name='all-news-list'),
       path("clean-old/", clean_old_news),
    path("clean-all/", delete_all_news),
    # New AI processing URLs
    path('process-news/', process_news_api, name='process-news'),
    path('news/<int:pk>/reprocess/', reprocess_news_api, name='reprocess-news'),
    path('processing-stats/', processing_stats_api, name='processing-stats'),
]