# core/views.py

from rest_framework import generics
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import NewsItem
from .serializers import NewsItemSerializer
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .ai_processor import process_unprocessed_news, reprocess_news_item
from .models import NewsItem
from .serializers import NewsItemSerializer 
from .scraper import run_scraper, save_to_db
from django.utils import timezone
from datetime import timedelta
from django.db import connection

class ProcessedNewsListAPIView(generics.ListAPIView):
    serializer_class = NewsItemSerializer
    filter_backends = [SearchFilter, OrderingFilter]

    # allow searching in title / summary
    search_fields = ['title', 'summary', 'ai_summary']

    # allow sorting by risk_score, priority, created_at
    ordering_fields = ['risk_score', 'priority', 'created_at']

    def get_queryset(self):
        return NewsItem.objects.filter(processed_by_llm=True).order_by('-risk_score')

class NewsDetailAPIView(generics.RetrieveAPIView):
    queryset = NewsItem.objects.all()
    serializer_class = NewsItemSerializer
    lookup_field = "id"
    
@api_view(['POST'])
def run_scraper_view(request):
    try:
        scraped_data = run_scraper()                 # returns dict {source: [items]}
        saved_items = save_to_db(scraped_data)       # returns list of saved objects

        return Response(
            {
                "message": "Scraping completed successfully.",
                "scraped_count": sum(len(v) for v in scraped_data.values()),
                "saved_to_db": len(saved_items),
            },
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

class AllNewsListAPIView(generics.ListAPIView):
    queryset = NewsItem.objects.all().order_by('-created_at')
    serializer_class = NewsItemSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['title', 'summary']
    ordering_fields = ['created_at', 'priority']

@api_view(['POST'])
def delete_all_news(request):
    try:
        deleted_count, _ = NewsItem.objects.all().delete()
        # 2. Reset SQLite autoincrement (PRIMARY KEY) to 1
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='core_newsitem';")


        return Response({
            "message": "All news deleted successfully.",
            "deleted_items": deleted_count,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def clean_old_news(request):
    try:
        days = request.data.get("days", 30)  # default: 30 days

        cutoff_date = timezone.now() - timedelta(days=days)

        deleted_count, _ = NewsItem.objects.filter(created_at__lt=cutoff_date).delete()

        return Response({
            "message": f"Old news deleted successfully.",
            "deleted_items": deleted_count,
            "retained_days": days
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['POST'])
def clean_old_news(request):
    try:
        days = request.data.get("days", 30)  # default: 30 days

        cutoff_date = timezone.now() - timedelta(days=days)

        deleted_count, _ = NewsItem.objects.filter(created_at__lt=cutoff_date).delete()

        return Response({
            "message": f"Old news deleted successfully.",
            "deleted_items": deleted_count,
            "retained_days": days
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
def clean_old_news(request):
    try:
        days = request.data.get("days", 30)  # default: 30 days

        cutoff_date = timezone.now() - timedelta(days=days)

        deleted_count, _ = NewsItem.objects.filter(created_at__lt=cutoff_date).delete()

        return Response({
            "message": f"Old news deleted successfully.",
            "deleted_items": deleted_count,
            "retained_days": days
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
@api_view(['POST'])
def process_news_api(request):
    """
    API endpoint to trigger news processing
    POST /api/process-news/
    
    Body (optional):
    {
        "batch_size": 10,
        "delay": 2
    }
    """
    try:
        batch_size = request.data.get('batch_size', 10)
        delay = request.data.get('delay', 2)
        
        result = process_unprocessed_news(batch_size=batch_size, delay=delay)
        
        return Response({
            'success': True,
            'message': 'Processing completed',
            'result': result
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def reprocess_news_api(request, pk):
    """
    API endpoint to reprocess a specific news item
    POST /api/news/{id}/reprocess/
    """
    try:
        success = reprocess_news_item(pk)
        
        if success:
            news_item = NewsItem.objects.get(pk=pk)
            serializer = NewsItemSerializer(news_item)
            return Response({
                'success': True,
                'message': 'News item reprocessed successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Failed to reprocess news item'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except NewsItem.DoesNotExist:
        return Response({
            'success': False,
            'error': 'News item not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def processing_stats_api(request):
    """
    Get statistics about news processing
    GET /api/processing-stats/
    """
    try:
        total = NewsItem.objects.count()
        processed = NewsItem.objects.filter(processed_by_llm=True).count()
        unprocessed = NewsItem.objects.filter(processed_by_llm=False).count()
        
        risk_breakdown = {}
        for level in ['critical', 'high', 'medium', 'low']:
            risk_breakdown[level] = NewsItem.objects.filter(
                processed_by_llm=True,
                risk_level=level
            ).count()
        
        return Response({
            'total_news': total,
            'processed': processed,
            'unprocessed': unprocessed,
            'processing_rate': f"{(processed/total*100):.1f}%" if total > 0 else "0%",
            'risk_breakdown': risk_breakdown
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
