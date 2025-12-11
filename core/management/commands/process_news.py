# core/management/commands/morning_news_update.py

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import NewsItem
from core.scraper import run_scraper, save_to_db
from core.ai_processor import process_high_priority_first, clear_content_cache, process_unprocessed_news
import time
from core.views import delete_all_news
from rest_framework.test import APIRequestFactory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Morning news update: Scrape, process, and clean old news'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workers',
            type=int,
            default=6,
            help='Number of parallel workers for processing (default: 6)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of articles to process (default: 50)'
        )
        parser.add_argument(
            '--clean-days',
            type=int,
            default=1,
            help='Delete news older than X days (default: 30)'
        )
        parser.add_argument(
            '--no-clean',
            action='store_true',
            help='Skip cleaning old news'
        )
        parser.add_argument(
            '--no-scrape',
            action='store_true',
            help='Skip scraping (only process existing)'
        )

    def handle(self, *args, **options):
        start_time = time.time()
        workers = options['workers']
        batch_size = options['batch_size']
        clean_days = options['clean_days']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🌅 MORNING NEWS UPDATE STARTED'))
        self.stdout.write(self.style.SUCCESS(f'⏰ Time: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Step 1: Clean old news (optional)
        if not options['no_clean']:
            self.stdout.write(self.style.WARNING('\n🧹 Step 1: Cleaning old news...'))
            self._clean_old_news(clean_days)
        else:
            self.stdout.write(self.style.WARNING('\n⏭️  Step 1: Skipping cleanup'))
        
        # Step 2: Scrape latest news
        if not options['no_scrape']:
            self.stdout.write(self.style.WARNING('\n📰 Step 2: Scraping latest news...'))
            scraped_count = self._scrape_news()
        else:
            self.stdout.write(self.style.WARNING('\n⏭️  Step 2: Skipping scraping'))
            scraped_count = 0
        
        # Step 3: Process high-priority news first
        self.stdout.write(self.style.WARNING(f'\n🤖 Step 3: Processing news (workers: {workers})...'))
        processed_stats = self._process_news(batch_size, workers)
        
        # Step 4: Generate summary report
        self.stdout.write(self.style.WARNING('\n📊 Step 4: Generating summary...'))
        summary = self._generate_summary()
        
        # Display results
        elapsed = time.time() - start_time
        self._display_results(scraped_count, processed_stats, summary, elapsed)
        
        # Clear cache for next run
        clear_content_cache()
        
        self.stdout.write(self.style.SUCCESS('\n✅ Morning news update completed!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
    def _clean_old_news(self, days):
        if days == -1:  # use -1 to indicate "delete all"
            factory = APIRequestFactory()
            request = factory.delete('/api/news/delete-all/')
            response = delete_all_news(request)

            self.stdout.write(self.style.ERROR(str(response.data)))
            return
    
    
    # def _clean_old_news(self, days):
    #     """Delete news older than specified days"""
    #     try:
    #         cutoff_date = timezone.now() - timedelta(days=days)
    #         deleted_count, _ = NewsItem.objects.filter(
    #             created_at__lt=cutoff_date
    #         ).delete()
            
    #         if deleted_count > 0:
    #             self.stdout.write(
    #                 self.style.SUCCESS(f'   ✓ Deleted {deleted_count} articles older than {days} days')
    #             )
    #         else:
    #             self.stdout.write(
    #                 self.style.SUCCESS(f'   ✓ No old articles to delete')
    #             )
                
    #     except Exception as e:
    #         self.stdout.write(
    #             self.style.ERROR(f'   ✗ Error cleaning old news: {str(e)}')
    #         )

    def _scrape_news(self):
        """Scrape latest news from all sources"""
        try:
            scraped_data = run_scraper()
            saved_items = save_to_db(scraped_data)
            
            total_scraped = sum(len(v) for v in scraped_data.values())
            total_saved = len(saved_items)
            duplicates = total_scraped - total_saved
            
            self.stdout.write(
                self.style.SUCCESS(f'   ✓ Scraped {total_scraped} articles')
            )
            self.stdout.write(
                self.style.SUCCESS(f'   ✓ Saved {total_saved} new articles')
            )
            if duplicates > 0:
                self.stdout.write(
                    self.style.WARNING(f'   ⓘ Skipped {duplicates} duplicates')
                )
            
            # Show breakdown by source
            self.stdout.write(self.style.SUCCESS('\n   Source breakdown:'))
            for source, items in scraped_data.items():
                if items:
                    high_priority = sum(1 for item in items if item.get('is_priority', False))
                    self.stdout.write(
                        f'   • {source}: {len(items)} articles ({high_priority} high-priority)'
                    )
            
            return total_saved
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ✗ Error scraping news: {str(e)}')
            )
            return 0

    def _process_news(self, batch_size, workers):
        """Process unprocessed news with AI"""
        try:
            # Process high-priority first
            result =  process_unprocessed_news(
                batch_size=batch_size,
                max_workers=workers
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'   ✓ Processed {result["processed"]} articles')
            )
            if result['failed'] > 0:
                self.stdout.write(
                    self.style.WARNING(f'   ⚠ Failed {result["failed"]} articles')
                )
            if result['skipped'] > 0:
                self.stdout.write(
                    self.style.WARNING(f'   ⓘ Skipped {result["skipped"]} articles')
                )
            
            return result
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ✗ Error processing news: {str(e)}')
            )
            return {'processed': 0, 'failed': 0, 'skipped': 0}

    def _generate_summary(self):
        """Generate statistics summary"""
        try:
            total = NewsItem.objects.count()
            processed = NewsItem.objects.filter(processed_by_llm=True).count()
            unprocessed = NewsItem.objects.filter(processed_by_llm=False).count()
            
            # Today's news
            today = timezone.now().date()
            today_news = NewsItem.objects.filter(created_at__date=today).count()
            
            # Risk breakdown
            critical = NewsItem.objects.filter(
                processed_by_llm=True, risk_level='critical'
            ).count()
            high = NewsItem.objects.filter(
                processed_by_llm=True, risk_level='high'
            ).count()
            medium = NewsItem.objects.filter(
                processed_by_llm=True, risk_level='medium'
            ).count()
            low = NewsItem.objects.filter(
                processed_by_llm=True, risk_level='low'
            ).count()
            
            # Priority breakdown
            high_priority = NewsItem.objects.filter(priority__gte=5).count()
            
            return {
                'total': total,
                'processed': processed,
                'unprocessed': unprocessed,
                'today_news': today_news,
                'critical': critical,
                'high': high,
                'medium': medium,
                'low': low,
                'high_priority': high_priority
            }
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'   ✗ Error generating summary: {str(e)}')
            )
            return {}

    def _display_results(self, scraped, processed_stats, summary, elapsed):
        """Display final results"""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('📈 SUMMARY REPORT'))
        self.stdout.write('=' * 60)
        
        # Scraping results
        self.stdout.write(self.style.WARNING('\n📰 Scraping:'))
        self.stdout.write(f'   New articles: {scraped}')
        
        # Processing results
        self.stdout.write(self.style.WARNING('\n🤖 Processing:'))
        self.stdout.write(f'   Processed: {processed_stats.get("processed", 0)}')
        self.stdout.write(f'   Failed: {processed_stats.get("failed", 0)}')
        self.stdout.write(f'   Skipped: {processed_stats.get("skipped", 0)}')
        
        # Database statistics
        if summary:
            self.stdout.write(self.style.WARNING('\n📊 Database Stats:'))
            self.stdout.write(f'   Total articles: {summary["total"]}')
            self.stdout.write(f'   Processed: {summary["processed"]} ({summary["processed"]/summary["total"]*100:.1f}%)' if summary["total"] > 0 else '   Processed: 0 (0%)')
            self.stdout.write(f'   Unprocessed: {summary["unprocessed"]}')
            self.stdout.write(f'   Today\'s news: {summary["today_news"]}')
            
            self.stdout.write(self.style.WARNING('\n🛡️ Risk Breakdown:'))
            self.stdout.write(self.style.ERROR(f'   Critical: {summary["critical"]}'))
            self.stdout.write(self.style.WARNING(f'   High: {summary["high"]}'))
            self.stdout.write(f'   Medium: {summary["medium"]}')
            self.stdout.write(f'   Low: {summary["low"]}')
            
            self.stdout.write(self.style.WARNING('\n⭐ Priority:'))
            self.stdout.write(f'   High priority (≥5): {summary["high_priority"]}')
        
        # Performance
        self.stdout.write(self.style.WARNING('\n⏱️ Performance:'))
        self.stdout.write(f'   Total time: {elapsed:.1f} seconds')
        self.stdout.write(f'   Avg per article: {elapsed/processed_stats.get("processed", 1):.1f}s' if processed_stats.get("processed", 0) > 0 else '   Avg per article: N/A')
        
        # Top critical/high priority items
        if summary.get('critical', 0) > 0 or summary.get('high', 0) > 0:
            self.stdout.write(self.style.WARNING('\n🚨 ATTENTION REQUIRED:'))
            
            # Get top 5 critical items
            critical_items = NewsItem.objects.filter(
                processed_by_llm=True,
                risk_level='critical'
            ).order_by('-risk_score', '-created_at')[:5]
            
            if critical_items:
                self.stdout.write(self.style.ERROR('\n   CRITICAL ITEMS:'))
                for item in critical_items:
                    self.stdout.write(
                        f'   • [{item.risk_score}/10] {item.title[:70]}...'
                    )
            
            # Get top 10 high priority items
            high_items = NewsItem.objects.filter(
                processed_by_llm=True,
                risk_level='high',
                priority__gte=10
            ).order_by('-priority', '-risk_score', '-created_at')[:5]
            
            if high_items:
                self.stdout.write(self.style.WARNING('\n   HIGH PRIORITY ITEMS:'))
                for item in high_items:
                    self.stdout.write(
                        f'   • [{item.priority}] {item.title[:70]}...'
                    )
                    
             # Show all processed news with AI summary
        self.stdout.write(self.style.WARNING('\n🧠 PROCESSED NEWS WITH AI SUMMARY:'))
        
        processed_items = NewsItem.objects.filter(processed_by_llm=True).order_by('-created_at')

        if not processed_items.exists():
            self.stdout.write('   No processed articles available.')
        else:
            for item in processed_items:
                self.stdout.write('\n' + '-' * 60)
                self.stdout.write(self.style.SUCCESS(f'📰 Title: {item.title}'))
                self.stdout.write(f'🔗 Source: {item.source}')
                self.stdout.write(f'⚠️  Risk Level: {item.risk_level.upper()}')
                self.stdout.write(f'⭐ Priority: {item.priority}')
                
                summary_text = item.ai_summary or "(No AI summary generated)"
                self.stdout.write(self.style.WARNING('\n📝 AI Summary:'))
                self.stdout.write(f'{summary_text}')