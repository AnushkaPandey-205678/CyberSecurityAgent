from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import timedelta
from django.db import connection
from django.db.models import Q
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from .models import NewsItem
from .serializers import NewsItemSerializer
from .ai_processor import (
    process_unprocessed_news, 
    reprocess_news_item,
    process_high_priority_first,
    clear_content_cache
)
from .scraper import run_scraper, save_to_db
from .agentic_processor import run_agentic_news_analysis, get_agent_top_10
import logging
logger = logging.getLogger(__name__)

# Custom pagination
class NewsItemPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET'])
def processed_news_list(request):
    """
    GET /api/news/processed/
    
    Query params:
    - priority: filter by priority (1-10)
    - risk_level: filter by risk (critical/high/medium/low)
    - search: search in title, summary, ai_summary
    - ordering: sort by field (risk_score, priority, created_at)
    - min_priority: minimum priority (e.g., 5 for high priority only)
    - page: page number
    - page_size: items per page (default: 20)
    """
    try:
        # Start with processed news
        queryset = NewsItem.objects.filter(processed_by_llm=True)
        
        # Filter by priority
        priority = request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=int(priority))
        
        # Filter by minimum priority
        min_priority = request.query_params.get('min_priority')
        if min_priority:
            queryset = queryset.filter(priority__gte=int(min_priority))
        
        # Filter by risk level
        risk_level = request.query_params.get('risk_level')
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level.lower())
        
        # Search functionality
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(summary__icontains=search) |
                Q(ai_summary__icontains=search)
            )
        
        # Ordering (default: -risk_score, -priority)
        ordering = request.query_params.get('ordering', '-risk_score,-priority')
        ordering_fields = [field.strip() for field in ordering.split(',')]
        queryset = queryset.order_by(*ordering_fields)
        
        # Pagination
        paginator = NewsItemPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            serializer = NewsItemSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        # Fallback without pagination
        serializer = NewsItemSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def all_news_list(request):
    """
    GET /api/news/all/
    
    Query params:
    - priority: filter by priority
    - min_priority: minimum priority
    - processed: true/false (filter by processing status)
    - search: search in title, summary
    - ordering: sort by field (default: -created_at)
    """
    try:
        queryset = NewsItem.objects.all()
        
        # Filter by priority
        priority = request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=int(priority))
        
        # Filter by minimum priority
        min_priority = request.query_params.get('min_priority')
        if min_priority:
            queryset = queryset.filter(priority__gte=int(min_priority))
        
        # Filter by processed status
        processed = request.query_params.get('processed')
        if processed:
            is_processed = processed.lower() == 'true'
            queryset = queryset.filter(processed_by_llm=is_processed)
        
        # Search
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(summary__icontains=search)
            )
        
        # Ordering
        ordering = request.query_params.get('ordering', '-created_at')
        ordering_fields = [field.strip() for field in ordering.split(',')]
        queryset = queryset.order_by(*ordering_fields)
        
        # Pagination
        paginator = NewsItemPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            serializer = NewsItemSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = NewsItemSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def high_priority_news_list(request):
    """
    GET /api/news/high-priority/
    
    Get only high priority news (priority >= 5)
    Ordered by: priority DESC, risk_score DESC, created_at DESC
    """
    try:
        queryset = NewsItem.objects.filter(
            processed_by_llm=True,
            priority__gte=5
        ).order_by('-priority', '-risk_score', '-created_at')
        
        # Search
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(ai_summary__icontains=search)
            )
        
        # Risk level filter
        risk_level = request.query_params.get('risk_level')
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level.lower())
        
        # Pagination
        paginator = NewsItemPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            serializer = NewsItemSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = NewsItemSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def critical_news_list(request):
    """
    GET /api/news/critical/
    
    Get only critical risk level news
    """
    try:
        queryset = NewsItem.objects.filter(
            processed_by_llm=True,
            risk_level='critical'
        ).order_by('-risk_score', '-created_at')
        
        paginator = NewsItemPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            serializer = NewsItemSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = NewsItemSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def news_by_priority(request, priority_level):
    """
    GET /api/news/priority/{priority_level}/
    
    Get news filtered by specific priority level (1-10)
    """
    try:
        queryset = NewsItem.objects.filter(
            priority=priority_level
        ).order_by('-risk_score', '-created_at')
        
        paginator = NewsItemPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            serializer = NewsItemSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = NewsItemSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def news_detail(request, pk):
    """
    GET /api/news/{id}/
    
    Get single news item details
    """
    try:
        news_item = NewsItem.objects.get(pk=pk)
        serializer = NewsItemSerializer(news_item)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except NewsItem.DoesNotExist:
        return Response({
            'error': 'News item not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
def update_news_priority(request, pk):
    """
    POST /api/news/{id}/update-priority/
    
    Body: {"priority": 8}
    """
    try:
        news_item = NewsItem.objects.get(pk=pk)
        priority = request.data.get('priority')
        
        if priority is None:
            return Response({
                'error': 'Priority value is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        priority = int(priority)
        if priority < 1 or priority > 10:
            return Response({
                'error': 'Priority must be between 1 and 10'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        news_item.priority = priority
        news_item.save()
        
        serializer = NewsItemSerializer(news_item)
        return Response({
            'message': 'Priority updated successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except NewsItem.DoesNotExist:
        return Response({
            'error': 'News item not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except ValueError:
        return Response({
            'error': 'Invalid priority value'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def run_scraper_view(request):
    """
    POST /api/scrape/
    
    Scrape news from configured sources
    """
    try:
        scraped_data = run_scraper()
        saved_items = save_to_db(scraped_data)

        return Response({
            "message": "Scraping completed successfully.",
            "scraped_count": sum(len(v) for v in scraped_data.values()),
            "saved_to_db": len(saved_items),
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_all_news(request):
    """
    POST /api/news/delete-all/
    
    Delete all news items and reset counter
    """
    try:
        deleted_count, _ = NewsItem.objects.all().delete()
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='core_newsitem';")

        clear_content_cache()

        return Response({
            "message": "All news deleted successfully.",
            "deleted_items": deleted_count,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def clean_old_news(request):
    """
    POST /api/news/clean-old/
    
    Body (optional): {"days": 30}
    """
    try:
        days = request.data.get("days", 30)
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count, _ = NewsItem.objects.filter(created_at__lt=cutoff_date).delete()

        return Response({
            "message": f"Old news deleted successfully.",
            "deleted_items": deleted_count,
            "retained_days": days
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def process_news_api(request):
    """
    POST /api/process-news/
    
    Body (optional):
    {
        "batch_size": 20,
        "parallel": true,
        "max_workers": 4,
        "high_priority_first": true
    }
    """
    try:
        batch_size = request.data.get('batch_size', 20)
        parallel = request.data.get('parallel', True)
        max_workers = request.data.get('max_workers', 4)
        high_priority = request.data.get('high_priority_first', True)
        
        if high_priority:
            result = process_high_priority_first(
                batch_size=batch_size,
                max_workers=max_workers
            )
        else:
            result = process_unprocessed_news(
                batch_size=batch_size,
                parallel=parallel,
                max_workers=max_workers
            )
        
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
    GET /api/processing-stats/
    
    Get comprehensive statistics about news processing
    """
    try:
        total = NewsItem.objects.count()
        processed = NewsItem.objects.filter(processed_by_llm=True).count()
        unprocessed = NewsItem.objects.filter(processed_by_llm=False).count()
        
        # Risk breakdown
        risk_breakdown = {}
        for level in ['critical', 'high', 'medium', 'low']:
            risk_breakdown[level] = NewsItem.objects.filter(
                processed_by_llm=True,
                risk_level=level
            ).count()
        
        # Priority breakdown
        priority_breakdown = {
            'critical_priority': NewsItem.objects.filter(priority__gte=8).count(),
            'high_priority': NewsItem.objects.filter(priority__gte=5, priority__lt=8).count(),
            'medium_priority': NewsItem.objects.filter(priority__gte=3, priority__lt=5).count(),
            'low_priority': NewsItem.objects.filter(priority__lt=3).count(),
        }
        
        # Source breakdown (top 5)
        from django.db.models import Count
        top_sources = NewsItem.objects.values('source').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        return Response({
            'total_news': total,
            'processed': processed,
            'unprocessed': unprocessed,
            'processing_rate': f"{(processed/total*100):.1f}%" if total > 0 else "0%",
            'risk_breakdown': risk_breakdown,
            'priority_breakdown': priority_breakdown,
            'top_sources': list(top_sources)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def scrape_and_process_api(request):
    """
    POST /api/scrape-and-process/
    
    Combined endpoint: Scrape news then immediately process them
    
    Body (optional):
    {
        "max_workers": 4,
        "high_priority_first": true
    }
    """
    try:
        # Step 1: Scrape news
        scraped_data = run_scraper()
        saved_items = save_to_db(scraped_data)
        
        # Step 2: Process the scraped news
        max_workers = request.data.get('max_workers', 4)
        high_priority = request.data.get('high_priority_first', True)
        
        if high_priority:
            process_result = process_high_priority_first(
                batch_size=len(saved_items),
                max_workers=max_workers
            )
        else:
            process_result = process_unprocessed_news(
                batch_size=len(saved_items),
                parallel=True,
                max_workers=max_workers
            )
        
        return Response({
            'success': True,
            'message': 'Scraping and processing completed',
            'scraping': {
                'scraped_count': sum(len(v) for v in scraped_data.values()),
                'saved_to_db': len(saved_items)
            },
            'processing': process_result
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def clear_cache_api(request):
    """
    POST /api/clear-cache/
    
    Clear the content extraction cache
    """
    try:
        clear_content_cache()
        return Response({
            'success': True,
            'message': 'Content cache cleared'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def dashboard_summary(request):
    """
    GET /api/dashboard-summary/
    
    Get quick dashboard summary for frontend
    """
    try:
        # Latest critical news
        critical_news = NewsItem.objects.filter(
            risk_level='critical',
            processed_by_llm=True
        ).order_by('-created_at')[:5]
        
        # Latest high priority news
        high_priority = NewsItem.objects.filter(
            priority__gte=5,
            processed_by_llm=True
        ).order_by('-created_at')[:10]
        
        # Recent unprocessed
        unprocessed_count = NewsItem.objects.filter(processed_by_llm=False).count()
        
        # Today's news
        today = timezone.now().date()
        today_news = NewsItem.objects.filter(
            created_at__date=today
        ).count()
        
        return Response({
            'critical_news': NewsItemSerializer(critical_news, many=True).data,
            'high_priority_news': NewsItemSerializer(high_priority, many=True).data,
            'unprocessed_count': unprocessed_count,
            'today_news_count': today_news,
            'last_updated': timezone.now()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

@api_view(['POST'])
@parser_classes([JSONParser, FormParser, MultiPartParser])  # Accept multiple content types
def scrape_and_agentic_analysis_api(request):
    """
    POST /api/scrape-and-analyze/
    
    Complete workflow:
    1. Scrape latest news from all sources
    2. Run agentic AI analysis to find top 10 most important
    
    Body (optional):
    {
        "hours": 24,
        "model": "llama3"
    }
    
    Or send as form data or empty POST
    """
    try:
        # Handle different content types
        if request.content_type and 'application/json' in request.content_type:
            hours = request.data.get('hours', 24)
            model = request.data.get('model', 'llama3')
        else:
            # Fallback for form data or empty requests
            hours = int(request.POST.get('hours', 24))
            model = request.POST.get('model', 'llama3')
        
        logger.info(f"Starting scrape and analyze: hours={hours}, model={model}")
        
        # Step 1: Scrape
        from .scraper import run_scraper, save_to_db
        logger.info("Step 1: Scraping news...")
        scraped_data = run_scraper()
        saved_items = save_to_db(scraped_data)
        
        scrape_count = len(saved_items)
        total_scraped = sum(len(v) for v in scraped_data.values())
        logger.info(f"Scraped {total_scraped} articles, saved {scrape_count} new ones")
        
        # If no new items, still analyze existing items from last X hours
        if scrape_count == 0:
            logger.warning("No new articles scraped (all duplicates), analyzing existing articles...")
        
        # Step 2: Agentic Analysis
        from .agentic_processor import run_agentic_news_analysis
        logger.info("Step 2: Running agentic AI analysis...")
        
        analysis_result = run_agentic_news_analysis(hours=hours, model=model)
        
        return Response({
            'success': True,
            'message': 'Scraping and agentic analysis completed',
            'scraping': {
                'total_found': total_scraped,
                'new_saved': scrape_count,
                'duplicates_skipped': total_scraped - scrape_count
            },
            'agentic_analysis': analysis_result
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception("Scrape and analyze failed")
        return Response({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def run_agentic_analysis_api(request):
    """
    POST /api/agentic-analysis/
    
    Run autonomous AI agent to analyze and prioritize news
    Handles JSON, form data, or empty POST
    """
    try:
        # Handle different content types
        if request.content_type and 'application/json' in request.content_type:
            hours = request.data.get('hours', 24)
            model = request.data.get('model', 'llama3')
        else:
            hours = int(request.POST.get('hours', 24))
            model = request.POST.get('model', 'llama3')
        
        logger.info(f"Running agentic analysis: hours={hours}, model={model}")
        
        from .agentic_processor import run_agentic_news_analysis
        result = run_agentic_news_analysis(hours=hours, model=model)
        
        return Response({
            'success': True,
            'message': 'Agentic analysis completed',
            'result': result
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception("Agentic analysis failed")
        return Response({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_agent_top_10_api(request):
    """
    GET /api/agent-top-10/
    
    Get the top 10 news items identified by the agentic AI
    """
    try:
        from .agentic_processor import get_agent_top_10
        top_10 = get_agent_top_10()
        
        results = []
        for item in top_10:
            try:
                risk_details = json.loads(item.risk_reason) if item.risk_reason else {}
            except:
                risk_details = {'raw': item.risk_reason}
            
            results.append({
                'id': item.id,
                'title': item.title,
                'source': item.source,
                'url': item.url,
                'executive_summary': item.ai_summary,
                'risk_level': item.risk_level,
                'risk_score': item.risk_score,
                'priority': item.priority,
                'details': risk_details,
                'created_at': item.created_at,
                'processed_at': item.processed_at
            })
        
        return Response({
            'success': True,
            'count': len(results),
            'top_10': results
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.exception("Failed to get agent top 10")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

