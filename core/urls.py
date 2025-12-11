# core/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # News List Views (with priority filtering)
    path('news/processed/', views.processed_news_list, name='processed-news-list'),
    path('news/all/', views.all_news_list, name='all-news-list'),
    path('news/high-priority/', views.high_priority_news_list, name='high-priority-news'),
    path('news/critical/', views.critical_news_list, name='critical-news'),
    path('news/priority/<int:priority_level>/', views.news_by_priority, name='news-by-priority'),
    
    # Single News Item
    path('news/<int:pk>/', views.news_detail, name='news-detail'),
    path('news/<int:pk>/update-priority/', views.update_news_priority, name='update-news-priority'),
    path('news/<int:pk>/reprocess/', views.reprocess_news_api, name='reprocess-news'),
    
    # Scraping
    path('scrape/', views.run_scraper_view, name='run-scraper'),
    path('scrape-and-process/', views.scrape_and_process_api, name='scrape-and-process'),
    
    # Processing
    path('process-news/', views.process_news_api, name='process-news'),
    
    # Statistics & Dashboard
    path('processing-stats/', views.processing_stats_api, name='processing-stats'),
    path('dashboard-summary/', views.dashboard_summary, name='dashboard-summary'),
    
    # Maintenance
    path('news/delete-all/', views.delete_all_news, name='delete-all-news'),
    path('news/clean-old/', views.clean_old_news, name='clean-old-news'),
    path('clear-cache/', views.clear_cache_api, name='clear-cache'),
]