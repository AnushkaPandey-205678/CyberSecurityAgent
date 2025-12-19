# core/management/commands/agentic_news_update.py

import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.scraper import run_scraper, save_to_db
from core.agentic_processor import AgenticNewsProcessor
import json

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run agentic AI analysis to find top 10 most important news in last 24 hours'

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
            '--scrape-first',
            action='store_true',
            help='Scrape new articles before analysis'
        )
        parser.add_argument(
            '--show-reasoning',
            action='store_true',
            help='Display agent reasoning and decision process'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        model = options['model']
        scrape_first = options['scrape_first']
        show_reasoning = options['show_reasoning']
        
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('🤖 AGENTIC AI NEWS ANALYSIS'))
        self.stdout.write(self.style.SUCCESS(f'⏰ Time: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}'))
        self.stdout.write(self.style.SUCCESS(f'🔍 Analyzing last {hours} hours'))
        self.stdout.write(self.style.SUCCESS(f'🧠 Model: {model}'))
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
        
        # Run agentic analysis
        self.stdout.write(self.style.WARNING('\n🤖 Running Agentic AI Analysis...\n'))
        
        try:
            agent = AgenticNewsProcessor(model=model)
            result = agent.run_agentic_analysis(hours=hours)
            
            if not result['success']:
                self.stdout.write(
                    self.style.ERROR(f'❌ Analysis failed: {result.get("message", "Unknown error")}')
                )
                return
            
            # Display results
            self._display_results(result, show_reasoning)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error during analysis: {str(e)}')
            )
            logger.exception("Agentic analysis failed")

    def _display_results(self, result, show_reasoning):
        """Display comprehensive results"""
        
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('📊 ANALYSIS RESULTS'))
        self.stdout.write('=' * 80)
        
        # Statistics
        self.stdout.write(self.style.WARNING('\n📈 Statistics:'))
        self.stdout.write(f'   Total articles analyzed: {result["total_analyzed"]}')
        self.stdout.write(f'   Top priority selected: {result["top_10_count"]}')
        self.stdout.write(f'   Processing time: {result["processing_time"]:.1f}s')
        
        # Agent reasoning (if requested)
        if show_reasoning:
            self.stdout.write(self.style.WARNING('\n🧠 Agent Reasoning:'))
            self.stdout.write(self._wrap_text(result.get('agent_reasoning', 'N/A'), 80))
            
            if result.get('identified_patterns'):
                self.stdout.write(self.style.WARNING('\n🔍 Identified Patterns:'))
                for pattern in result['identified_patterns']:
                    self.stdout.write(f'   • {pattern}')
            
            if result.get('recommended_actions'):
                self.stdout.write(self.style.WARNING('\n⚡ Recommended Actions:'))
                for action in result['recommended_actions']:
                    self.stdout.write(f'   • {action}')
        
        # Top 10 items
        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(self.style.SUCCESS('🎯 TOP 10 MOST IMPORTANT NEWS'))
        self.stdout.write('=' * 80 + '\n')
        
        for idx, item in enumerate(result['top_10_items'], 1):
            self._display_news_item(idx, item)

    def _display_news_item(self, idx, item):
        """Display individual news item"""
        
        # Header with ranking and risk
        risk_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }
        
        emoji = risk_emoji.get(item['risk_level'], '⚪')
        
        self.stdout.write(self.style.SUCCESS(f'[{idx}/10] {emoji} {item["risk_level"].upper()} (Score: {item["risk_score"]}/10)'))
        self.stdout.write('-' * 80)
        
        # Title and source
        self.stdout.write(self.style.WARNING(f'📰 {item["title"]}'))
        self.stdout.write(f'🔗 {item["url"]}')
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n📝 Executive Summary:'))
        summary = self._wrap_text(item['summary'], 76)
        self.stdout.write(f'   {summary}')
        
        self.stdout.write('\n')

    def _wrap_text(self, text, width):
        """Wrap long text to specified width"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n   '.join(lines)


# USAGE EXAMPLES:
# 
# Basic usage (analyze last 24 hours):
# python manage.py agentic_news_update
#
# Scrape first then analyze:
# python manage.py agentic_news_update --scrape-first
#
# Show agent reasoning:
# python manage.py agentic_news_update --show-reasoning
#
# Custom timeframe and model:
# python manage.py agentic_news_update --hours 48 --model mistral
#
# Full workflow:
# python manage.py agentic_news_update --scrape-first --show-reasoning