# core/management/commands/agentic_news_update.py

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.scraper import run_scraper, save_to_db
from core.agentic_processor import AgenticNewsProcessor
import json

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run comprehensive agentic AI analysis to find top most important news'

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
            default=4,
            help='Number of parallel workers (default: 4, recommended 2-6)'
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
            '--scrape-first',
            action='store_true',
            help='Scrape new articles before analysis'
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
        scrape_first = options['scrape_first']
        show_reasoning = options['show_reasoning']
        show_details = options['show_details']
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('🤖 COMPREHENSIVE AGENTIC AI NEWS ANALYSIS'))
        self.stdout.write(self.style.SUCCESS(f'⏰ Time: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'))
        self.stdout.write(self.style.SUCCESS(f'🔍 Analyzing last {hours} hours'))
        self.stdout.write(self.style.SUCCESS(f'🧠 Model: {model}'))
        self.stdout.write(self.style.SUCCESS(f'⚙️  Workers: {workers} (quality-focused)'))
        self.stdout.write(self.style.SUCCESS(f'🎯 Top items: {top_n}'))
        if limit:
            self.stdout.write(self.style.SUCCESS(f'📊 Item limit: {limit}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'📊 Item limit: All items'))
        self.stdout.write(self.style.WARNING('⏱️  Note: Comprehensive analysis prioritizes quality over speed'))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        
        # Optional: Scrape first
        if scrape_first:
            self.stdout.write(self.style.WARNING('\n📰 Step 0: Scraping latest news...'))
            try:
                scraped_data = run_scraper()
                saved_items = save_to_db(scraped_data)
                self.stdout.write(
                    self.style.SUCCESS(f'   ✓ Scraped and saved {len(saved_items)} new articles')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'   ✗ Scraping failed: {str(e)}')
                )
        
        # Run comprehensive agentic analysis
        self.stdout.write(self.style.WARNING('\n🤖 Running Comprehensive Agentic AI Analysis...'))
        self.stdout.write(self.style.WARNING('   This may take several minutes for thorough analysis...\n'))
        
        try:
            agent = AgenticNewsProcessor(model=model, max_workers=workers)
            result = agent.run_agentic_analysis(hours=hours, limit=limit, top_n=top_n)
            
            if not result['success']:
                self.stdout.write(
                    self.style.ERROR(f'❌ Analysis failed: {result.get("message", "Unknown error")}')
                )
                return
            
            # Display results
            self._display_results(result, show_reasoning, show_details)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error during analysis: {str(e)}')
            )
            logger.exception("Comprehensive agentic analysis failed")

    def _display_results(self, result, show_reasoning, show_details):
        """Display comprehensive results"""
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('📊 ANALYSIS RESULTS'))
        self.stdout.write('=' * 80)
        
        # Statistics
        self.stdout.write(self.style.WARNING('\n📈 Statistics:'))
        self.stdout.write(f'   Total articles analyzed: {result["total_analyzed"]}')
        self.stdout.write(f'   Top priority selected: {result["top_items_count"]}')
        self.stdout.write(f'   Processing time: {result["processing_time_minutes"]:.2f} minutes ({result["processing_time_seconds"]:.1f}s)')
        self.stdout.write(f'   Parallel workers used: {result["parallel_workers"]}')
        
        # Agent reasoning (if requested)
        if show_reasoning and result.get('agent_reasoning'):
            self.stdout.write(self.style.WARNING('\n🧠 Agent Strategic Assessment:'))
            self.stdout.write(self._wrap_text(result['agent_reasoning'], 76))
            
            if result.get('identified_patterns'):
                self.stdout.write(self.style.WARNING('\n🔍 Identified Patterns:'))
                for pattern in result['identified_patterns']:
                    self.stdout.write(f'   • {pattern}')
        
        # Top N items
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS(f'🎯 TOP {result["top_items_count"]} MOST IMPORTANT NEWS'))
        self.stdout.write('=' * 80 + '\n')
        
        for idx, item in enumerate(result['top_items'], 1):
            self._display_news_item(idx, item, show_details)

    def _display_news_item(self, idx, item, show_details=False):
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
            f'[{idx}/{len(item)}] {emoji} {item["risk_level"].upper()} '
            f'(Risk Score: {item["risk_score"]}/10)'
        ))
        self.stdout.write('-' * 80)
        
        # Title
        self.stdout.write(self.style.WARNING(f'📰 {item["title"]}'))
        
        # Published date
        if item.get('published'):
            self.stdout.write(f'📅 Published: {item["published"]}')
        
        # URL
        self.stdout.write(f'🔗 {item["url"]}')
        
        # Comprehensive Summary
        if item.get('summary'):
            self.stdout.write(self.style.SUCCESS('\n📝 Comprehensive Summary:'))
            summary = self._wrap_text(item['summary'], 76)
            for line in summary.split('\n'):
                self.stdout.write(f'   {line}')
        
        # Detailed view (if requested)
        if show_details:
            self._display_detailed_analysis(item)
        
        self.stdout.write('\n')

    def _display_detailed_analysis(self, item):
        """Display detailed analysis information"""
        
        # Try to parse risk_reason if it contains JSON
        try:
            # This would be populated from the database field
            # For now, we'll check if there's any additional data in the item
            if 'risk_reason' in item:
                risk_data = json.loads(item['risk_reason']) if isinstance(item['risk_reason'], str) else item['risk_reason']
                
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
                
                if risk_data.get('risk_reasoning'):
                    self.stdout.write(self.style.WARNING('\n🔍 Risk Assessment Reasoning:'))
                    reasoning = self._wrap_text(risk_data['risk_reasoning'], 76)
                    for line in reasoning.split('\n'):
                        self.stdout.write(f'   {line}')
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
# Basic usage (analyze last 24 hours, comprehensive mode):
# python manage.py agentic_news_update
#
# Scrape first then analyze:
# python manage.py agentic_news_update --scrape-first
#
# Show agent reasoning and patterns:
# python manage.py agentic_news_update --show-reasoning
#
# Show full detailed analysis for each item:
# python manage.py agentic_news_update --show-details
#
# Custom timeframe and top items:
# python manage.py agentic_news_update --hours 48 --top-n 20
#
# Limit number of items to analyze (for faster testing):
# python manage.py agentic_news_update --limit 30
#
# Adjust parallel workers (2-6 recommended for quality):
# python manage.py agentic_news_update --workers 2
#
# Use different model:
# python manage.py agentic_news_update --model mistral
#
# Full comprehensive workflow with all details:
# python manage.py agentic_news_update --scrape-first --show-reasoning --show-details --top-n 15
#
# Quick test on limited dataset:
# python manage.py agentic_news_update --limit 10 --top-n 5 --workers 2