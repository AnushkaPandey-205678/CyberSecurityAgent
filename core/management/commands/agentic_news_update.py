# core/management/commands/agentic_news_update.py

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.scraper import run_scraper, save_to_db
from core.agentic_processor import AgenticNewsProcessor
from core.models import NewsItem
import json

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scrape latest news and run agentic AI analysis to find top 10 most important cybersecurity news'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Analyze news from last X hours (default: 24)'
        )
        parser.add_argument(
            '--model',
            type=str,
            default='llama3',
            help='Ollama model to use (default: llama3)'
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=3,
            help='Number of parallel workers (default: 3, recommended 2-4 to avoid timeouts)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of items to analyze (default: all)'
        )
        parser.add_argument(
            '--top-n',
            type=int,
            default=10,
            help='Number of top items to select for deep analysis (default: 10)'
        )
        parser.add_argument(
            '--skip-scrape',
            action='store_true',
            help='Skip scraping and only analyze existing news'
        )
        parser.add_argument(
            '--show-reasoning',
            action='store_true',
            help='Display agent reasoning and decision process'
        )
        parser.add_argument(
            '--show-details',
            action='store_true',
            help='Show detailed analysis for each item'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        model = options['model']
        workers = options['workers']
        limit = options['limit']
        top_n = options['top_n']
        skip_scrape = options['skip_scrape']
        show_reasoning = options['show_reasoning']
        show_details = options['show_details']
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('🤖 CYBERSECURITY NEWS SCRAPER & AGENTIC AI ANALYSIS'))
        self.stdout.write(self.style.SUCCESS(f'⏰ Time: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'))
        self.stdout.write(self.style.SUCCESS(f'🔍 Analyzing last {hours} hours'))
        self.stdout.write(self.style.SUCCESS(f'🧠 Model: {model}'))
        self.stdout.write(self.style.SUCCESS(f'⚙️  Workers: {workers} (optimized for reliability)'))
        self.stdout.write(self.style.SUCCESS(f'🎯 Top items: {top_n}'))
        if limit:
            self.stdout.write(self.style.SUCCESS(f'📊 Item limit: {limit}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'📊 Item limit: All items'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        
        # STEP 1: Scrape latest cybersecurity news
        if not skip_scrape:
            self.stdout.write(self.style.WARNING('\n📰 STEP 1: Scraping Latest Cybersecurity News...'))
            self.stdout.write(self.style.WARNING('   Fetching articles from trusted security sources...\n'))
            
            try:
                scraped_data = run_scraper()
                saved_items = save_to_db(scraped_data)
                
                total_scraped = sum(len(v) for v in scraped_data.values())
                
                self.stdout.write(self.style.SUCCESS(f'\n   ✅ Scraping Complete!'))
                self.stdout.write(f'      Total articles found: {total_scraped}')
                self.stdout.write(f'      New articles saved: {len(saved_items)}')
                self.stdout.write(f'      Duplicates skipped: {total_scraped - len(saved_items)}')
                
                if len(saved_items) == 0:
                    self.stdout.write(self.style.WARNING(
                        '\n   ⚠️  No new articles found (all duplicates). Analyzing existing articles...'
                    ))
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'\n   ❌ Scraping failed: {str(e)}')
                )
                self.stdout.write(self.style.WARNING('   Continuing with existing articles in database...'))
        else:
            self.stdout.write(self.style.WARNING('\n📰 STEP 1: Skipping scrape (using existing articles)'))
        
        # Show database stats
        total_in_db = NewsItem.objects.count()
        unprocessed = NewsItem.objects.filter(processed_by_llm=False).count()
        
        self.stdout.write(f'\n   📊 Database Status:')
        self.stdout.write(f'      Total articles: {total_in_db}')
        self.stdout.write(f'      Unprocessed: {unprocessed}')
        
        # STEP 2: Run agentic AI analysis
        self.stdout.write(self.style.WARNING('\n🤖 STEP 2: Running Agentic AI Analysis...'))
        self.stdout.write(self.style.WARNING('   Phase 1: Keyword filtering (instant)'))
        self.stdout.write(self.style.WARNING('   Phase 2: Quick LLM scoring (batched)'))
        self.stdout.write(self.style.WARNING('   Phase 3: Deep analysis of top 10 (comprehensive)'))
        self.stdout.write(self.style.WARNING(f'   Expected time: 10-15 minutes\n'))
        
        try:
            agent = AgenticNewsProcessor(model=model, max_workers=workers)
            result = agent.run_agentic_analysis(hours=hours, limit=limit, top_n=top_n)
            
            if not result['success']:
                self.stdout.write(
                    self.style.ERROR(f'\n❌ Analysis failed: {result.get("message", "Unknown error")}')
                )
                return
            
            # Display results
            self._display_results(result, show_reasoning, show_details)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ Error during analysis: {str(e)}')
            )
            logger.exception("Agentic analysis failed")

    def _display_results(self, result, show_reasoning, show_details):
        """Display comprehensive results"""
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('📊 ANALYSIS RESULTS'))
        self.stdout.write('=' * 80)
        
        # Statistics
        self.stdout.write(self.style.WARNING('\n📈 Statistics:'))
        self.stdout.write(f'   Total articles analyzed: {result["total_analyzed"]}')
        if result.get('candidates_evaluated'):
            self.stdout.write(f'   Candidates for deep analysis: {result["candidates_evaluated"]}')
        self.stdout.write(f'   Top priority selected: {result["top_items_count"]}')
        self.stdout.write(f'   Processing time: {result["processing_time_minutes"]:.2f} minutes ({result["processing_time_seconds"]:.1f}s)')
        self.stdout.write(f'   Parallel workers used: {result["parallel_workers"]}')
        if result.get('items_per_minute'):
            self.stdout.write(f'   Processing speed: {result["items_per_minute"]:.1f} items/minute')
        
        # Identified patterns
        if result.get('identified_patterns'):
            self.stdout.write(self.style.WARNING('\n🔍 Identified Threat Patterns:'))
            for pattern in result['identified_patterns']:
                self.stdout.write(f'   • {pattern}')
        
        # Top N items
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS(f'🎯 TOP {result["top_items_count"]} MOST IMPORTANT CYBERSECURITY NEWS'))
        self.stdout.write('=' * 80 + '\n')
        
        for idx, item in enumerate(result['top_items'], 1):
            self._display_news_item(idx, item, result["top_items_count"], show_details)

    def _display_news_item(self, idx, item, total_items, show_details=False):
        """Display individual news item with comprehensive details"""
        
        # Header with ranking and risk
        risk_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }
        
        emoji = risk_emoji.get(item['risk_level'], '⚪')
        
        self.stdout.write(self.style.SUCCESS(
            f'[{idx}/{total_items}] {emoji} {item["risk_level"].upper()} '
            f'(Risk Score: {item["risk_score"]}/10)'
        ))
        self.stdout.write('-' * 80)
        
        # Title
        self.stdout.write(self.style.WARNING(f'📰 {item["title"]}'))
        
        # Source
        if item.get('source'):
            self.stdout.write(f'📡 Source: {item.get("source", "Unknown")}')
        
        # Published date
        if item.get('published') and item['published'] != 'None':
            self.stdout.write(f'📅 Published: {item["published"]}')
        
        # URL
        self.stdout.write(f'🔗 {item["url"]}')
        
        # Comprehensive Summary
        if item.get('summary'):
            self.stdout.write(self.style.SUCCESS('\n📝 AI Analysis Summary:'))
            summary = self._wrap_text(item['summary'], 76)
            for line in summary.split('\n'):
                self.stdout.write(f'   {line}')
        
        # Detailed view (if requested)
        if show_details:
            self._display_detailed_analysis(item)
        
        self.stdout.write('\n')

    def _display_detailed_analysis(self, item):
        """Display detailed analysis information"""
        
        # Get risk_reason from NewsItem if available
        try:
            news_item = NewsItem.objects.get(id=item['id'])
            if news_item.risk_reason:
                risk_data = json.loads(news_item.risk_reason) if isinstance(news_item.risk_reason, str) else news_item.risk_reason
                
                if risk_data.get('affected_systems'):
                    self.stdout.write(self.style.WARNING('\n🎯 Affected Systems:'))
                    for system in risk_data['affected_systems']:
                        self.stdout.write(f'   • {system}')
                
                if risk_data.get('affected_users'):
                    self.stdout.write(self.style.WARNING('\n👥 Affected Users:'))
                    self.stdout.write(f'   {risk_data["affected_users"]}')
                
                if risk_data.get('business_impact'):
                    self.stdout.write(self.style.WARNING('\n💼 Business Impact:'))
                    impact = self._wrap_text(risk_data['business_impact'], 76)
                    for line in impact.split('\n'):
                        self.stdout.write(f'   {line}')
                
                if risk_data.get('immediate_actions'):
                    self.stdout.write(self.style.WARNING('\n⚡ Immediate Actions:'))
                    for action in risk_data['immediate_actions']:
                        self.stdout.write(f'   • {action}')
                
                if risk_data.get('long_term_recommendations'):
                    self.stdout.write(self.style.WARNING('\n📋 Long-term Recommendations:'))
                    for rec in risk_data['long_term_recommendations']:
                        self.stdout.write(f'   • {rec}')
                
                if risk_data.get('indicators_of_compromise'):
                    iocs = risk_data['indicators_of_compromise']
                    if iocs and len(iocs) > 0 and iocs[0]:
                        self.stdout.write(self.style.WARNING('\n🚨 Indicators of Compromise:'))
                        for ioc in iocs:
                            if ioc:
                                self.stdout.write(f'   • {ioc}')
                
                if risk_data.get('risk_reasoning'):
                    self.stdout.write(self.style.WARNING('\n🔍 Risk Assessment Reasoning:'))
                    reasoning = self._wrap_text(risk_data['risk_reasoning'], 76)
                    for line in reasoning.split('\n'):
                        self.stdout.write(f'   {line}')
                        
        except NewsItem.DoesNotExist:
            logger.debug(f"Could not find news item {item.get('id')}")
        except Exception as e:
            logger.debug(f"Could not parse detailed analysis: {e}")

    def _wrap_text(self, text, width):
        """Wrap long text to specified width, preserving paragraphs"""
        if not text:
            return ""
        
        # Split into paragraphs
        paragraphs = text.split('\n\n')
        wrapped_paragraphs = []
        
        for paragraph in paragraphs:
            # Clean up the paragraph
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Wrap the paragraph
            words = paragraph.split()
            lines = []
            current_line = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 <= width:
                    current_line.append(word)
                    current_length += len(word) + 1
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            wrapped_paragraphs.append('\n   '.join(lines))
        
        return '\n\n   '.join(wrapped_paragraphs)


# USAGE EXAMPLES:
# 
# Basic usage (scrape + analyze last 24 hours):
# python manage.py agentic_news_update
#
# Show full details for each news item:
# python manage.py agentic_news_update --show-details
#
# Analyze longer timeframe:
# python manage.py agentic_news_update --hours 48 --top-n 20
#
# Only analyze existing articles (skip scraping):
# python manage.py agentic_news_update --skip-scrape
#
# Adjust parallel workers (2-4 recommended to avoid timeouts):
# python manage.py agentic_news_update --workers 2
#
# Use different model:
# python manage.py agentic_news_update --model mistral
#
# Full comprehensive workflow with all details:
# python manage.py agentic_news_update --show-details --top-n 15
#
# Quick test on limited dataset:
# python manage.py agentic_news_update --limit 30 --top-n 5 --workers 2