# core/management/commands/process_news.py

from django.core.management.base import BaseCommand
from core.ai_processor import process_unprocessed_news, reprocess_news_item
from core.models import NewsItem


class Command(BaseCommand):
    help = 'Process unprocessed news items with Ollama AI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of items to process in one run'
        )
        parser.add_argument(
            '--delay',
            type=int,
            default=2,
            help='Delay between processing items in seconds'
        )
        parser.add_argument(
            '--reprocess',
            type=int,
            help='Reprocess a specific news item by ID'
        )
        parser.add_argument(
            '--reprocess-all',
            action='store_true',
            help='Reprocess all news items (mark all as unprocessed)'
        )

    def handle(self, *args, **options):
        if options['reprocess']:
            news_id = options['reprocess']
            self.stdout.write(f'Reprocessing news item {news_id}...')
            success = reprocess_news_item(news_id)
            if success:
                self.stdout.write(self.style.SUCCESS(f'Successfully reprocessed item {news_id}'))
            else:
                self.stdout.write(self.style.ERROR(f'Failed to reprocess item {news_id}'))
            return
        
        if options['reprocess_all']:
            count = NewsItem.objects.update(processed_by_llm=False)
            self.stdout.write(self.style.WARNING(f'Marked {count} items for reprocessing'))
            return
        
        batch_size = options['batch_size']
        delay = options['delay']
        
        self.stdout.write(f'Processing up to {batch_size} unprocessed news items...')
        
        result = process_unprocessed_news(batch_size=batch_size, delay=delay)
        
        self.stdout.write(self.style.SUCCESS(
            f"\nProcessing complete!\n"
            f"Total: {result['total']}\n"
            f"Processed: {result['processed']}\n"
            f"Failed: {result['failed']}"
        ))
