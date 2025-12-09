# core/ai_processor.py

import requests
import time
from bs4 import BeautifulSoup
from ollama import Client
from django.utils import timezone
from .models import NewsItem
import json
import logging

logger = logging.getLogger(__name__)

# Initialize Ollama client
ollama_client = Client(host="http://localhost:11434")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def extract_article_content(url, max_retries=3):
    """
    Fetch and extract main content from article URL
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                tag.decompose()
            
            # Try multiple content selectors
            content_selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content',
                'main',
                '[role="main"]',
            ]
            
            content = None
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(separator=' ', strip=True)
                    break
            
            # Fallback: get all paragraphs
            if not content or len(content) < 200:
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text(strip=True) for p in paragraphs])
            
            # Clean and truncate content (Ollama has token limits)
            content = ' '.join(content.split())  # Remove extra whitespace
            
            # Limit to approximately 3000 words for better processing
            words = content.split()
            if len(words) > 3000:
                content = ' '.join(words[:3000]) + '...'
            
            return content if content else None
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            continue
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return None
    
    return None


def generate_ai_summary_with_ollama(title, content, url):
    """
    Generate AI summary and risk assessment using Ollama
    """
    try:
        # Create a focused prompt for cybersecurity analysis
        prompt = f"""You are a cybersecurity expert analyst. Analyze this cybersecurity news article and provide a comprehensive assessment.

Title: {title}
URL: {url}
Content: {content[:5000]}...

Please provide:
1. A clear, concise summary (3-5 sentences) highlighting the key cybersecurity implications
2. Risk assessment (Critical/High/Medium/Low) based on:
   - Potential impact on organizations
   - Severity of vulnerabilities or threats
   - Scope of affected systems
3. Risk score (1-10 scale)
4. Detailed reasoning for the risk assessment (2-3 sentences)

Respond ONLY with valid JSON in this exact format:
{{
  "ai_summary": "Your detailed summary here",
  "risk_level": "high",
  "risk_score": 8,
  "risk_reason": "Your reasoning here"
}}"""

        # Call Ollama API
        response = ollama_client.chat(
            model="llama3",  # or "llama3.1", "mistral", etc.
            messages=[
                {
                    "role": "system",
                    "content": "You are a cybersecurity expert. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "temperature": 0.3,  # Lower temperature for more focused responses
                "num_predict": 500,  # Limit response length
            }
        )
        
        # Extract response content
        response_text = response['message']['content'].strip()
        
        # Try to extract JSON from response
        # Sometimes LLMs add markdown code blocks
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        # Parse JSON response
        result = json.loads(response_text)
        
        # Validate and normalize risk_level
        risk_level = result.get('risk_level', 'low').lower()
        if risk_level not in ['critical', 'high', 'medium', 'low']:
            risk_level = 'low'
        
        # Validate risk_score
        risk_score = int(result.get('risk_score', 1))
        if risk_score < 1:
            risk_score = 1
        elif risk_score > 10:
            risk_score = 10
        
        return {
            'ai_summary': result.get('ai_summary', 'Summary generation failed.'),
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_reason': result.get('risk_reason', 'No reasoning provided.')
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}\nResponse: {response_text}")
        return {
            'ai_summary': f"Analysis for: {title}. Content extraction successful but structured analysis failed.",
            'risk_level': 'low',
            'risk_score': 1,
            'risk_reason': 'Automated analysis incomplete.'
        }
    except Exception as e:
        logger.error(f"Error generating summary with Ollama: {e}")
        return {
            'ai_summary': f"Failed to generate AI summary for: {title}",
            'risk_level': 'low',
            'risk_score': 1,
            'risk_reason': f'Processing error: {str(e)}'
        }


def process_single_news_item(news_item):
    """
    Process a single news item: fetch content, generate summary, update DB
    """
    try:
        logger.info(f"Processing news item {news_item.id}: {news_item.title}")
        
        # Skip if already processed
        if news_item.processed_by_llm:
            logger.info(f"News item {news_item.id} already processed. Skipping.")
            return False
        
        # Skip if no URL
        if not news_item.url:
            logger.warning(f"News item {news_item.id} has no URL. Skipping.")
            news_item.processed_by_llm = True
            news_item.ai_summary = "No URL available for content extraction."
            news_item.save()
            return False
        
        # Extract article content
        logger.info(f"Extracting content from: {news_item.url}")
        content = extract_article_content(news_item.url)
        
        if not content:
            logger.warning(f"Failed to extract content from {news_item.url}")
            news_item.processed_by_llm = True
            news_item.ai_summary = "Content extraction failed for this article."
            news_item.content = ""
            news_item.save()
            return False
        
        # Store extracted content
        news_item.content = content[:5000]  # Limit stored content size
        
        # Generate AI summary using Ollama
        logger.info(f"Generating AI summary for news item {news_item.id}")
        ai_result = generate_ai_summary_with_ollama(
            news_item.title,
            content,
            news_item.url
        )
        
        # Update news item with AI analysis
        news_item.ai_summary = ai_result['ai_summary']
        news_item.risk_level = ai_result['risk_level']
        news_item.risk_score = ai_result['risk_score']
        news_item.risk_reason = ai_result['risk_reason']
        news_item.processed_by_llm = True
        news_item.processed_at = timezone.now()
        
        news_item.save()
        
        logger.info(f"Successfully processed news item {news_item.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing news item {news_item.id}: {e}")
        news_item.ai_summary = f"Processing error: {str(e)}"
        news_item.processed_by_llm = True
        news_item.save()
        return False


def process_unprocessed_news(batch_size=10, delay=2):
    """
    Process all unprocessed news items in batches
    
    Args:
        batch_size: Number of items to process in one run
        delay: Delay between processing items (seconds)
    """
    unprocessed = NewsItem.objects.filter(processed_by_llm=False)[:batch_size]
    
    total = unprocessed.count()
    processed = 0
    failed = 0
    
    logger.info(f"Starting processing of {total} unprocessed news items")
    
    for idx, news_item in enumerate(unprocessed, 1):
        logger.info(f"Processing item {idx}/{total}")
        
        success = process_single_news_item(news_item)
        
        if success:
            processed += 1
        else:
            failed += 1
        
        # Add delay between requests to be respectful
        if idx < total:
            time.sleep(delay)
    
    logger.info(f"Processing complete. Processed: {processed}, Failed: {failed}")
    
    return {
        'total': total,
        'processed': processed,
        'failed': failed
    }


def reprocess_news_item(news_id):
    """
    Reprocess a specific news item by ID
    """
    try:
        news_item = NewsItem.objects.get(id=news_id)
        news_item.processed_by_llm = False
        news_item.save()
        
        return process_single_news_item(news_item)
    except NewsItem.DoesNotExist:
        logger.error(f"News item {news_id} not found")
        return False