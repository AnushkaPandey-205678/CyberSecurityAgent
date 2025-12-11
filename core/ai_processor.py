import requests
import time
from bs4 import BeautifulSoup
from ollama import Client
from django.utils import timezone
from .models import NewsItem
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)

# Initialize Ollama client with timeout
ollama_client = Client(host="http://localhost:11434", timeout=30)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Content extraction cache to avoid re-fetching
CONTENT_CACHE = {}


def extract_article_content(url, max_retries=2):
    """
    Fetch and extract main content from article URL - OPTIMIZED
    """
    # Check cache first
    url_hash = hashlib.md5(url.encode()).hexdigest()
    if url_hash in CONTENT_CACHE:
        return CONTENT_CACHE[url_hash]
    
    for attempt in range(max_retries):
        try:
            # Reduced timeout for faster failure
            response = requests.get(url, headers=HEADERS, timeout=8)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements - optimized selector
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'form', 'button']):
                tag.decompose()
            
            # Priority-ordered content selectors (most specific first)
            content_selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.entry-content',
                'main',
                '.content',
            ]
            
            content = None
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(separator=' ', strip=True)
                    if len(content) > 200:  # Valid content threshold
                        break
            
            # Fallback: get all paragraphs
            if not content or len(content) < 200:
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50])
            
            # Clean and truncate content
            content = ' '.join(content.split())
            
            # Reduced word limit for faster processing (1500 words ~ 2000 tokens)
            words = content.split()
            if len(words) > 1500:
                content = ' '.join(words[:1500])
            
            # Cache the result
            if content and len(content) > 100:
                CONTENT_CACHE[url_hash] = content
                return content
            
            return None
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout for {url} on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(1)
            continue
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return None
    
    return None


def generate_ai_summary_with_ollama(title, content, url):
    """
    Generate AI summary and risk assessment using Ollama - OPTIMIZED
    """
    try:
        # Shortened, more focused prompt for faster processing
        prompt = f"""Analyze this cybersecurity news and respond with ONLY valid JSON:

Title: {title}
Content: {content[:2500]}

Provide:
1. Summary (2-3 sentences max)
2. Risk level: critical/high/medium/low
3. Risk score: 1-10
4. Risk reason (1-2 sentences)

JSON format:
{{"ai_summary": "...", "risk_level": "...", "risk_score": X, "risk_reason": "..."}}"""

        # Optimized Ollama parameters
        response = ollama_client.chat(
            model="llama3",  # Use llama3.2 or mistral for faster inference if available
            messages=[
                {
                    "role": "system",
                    "content": "You are a cybersecurity analyst. Respond with ONLY JSON, no markdown."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            options={
                "temperature": 0.2,  # Lower for faster, more deterministic responses
                "num_predict": 300,  # Reduced token limit
                "top_p": 0.9,
                "top_k": 40,
                "num_ctx": 2048,  # Reduced context window
            }
        )
        
        # Extract and clean response
        response_text = response['message']['content'].strip()
        
        # Remove markdown code blocks if present
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        # Find JSON object in response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            response_text = response_text[start_idx:end_idx]
        
        # Parse JSON
        result = json.loads(response_text)
        
        # Validate and normalize
        risk_level = result.get('risk_level', 'low').lower()
        if risk_level not in ['critical', 'high', 'medium', 'low']:
            risk_level = 'medium'  # Default to medium instead of low
        
        risk_score = min(10, max(1, int(result.get('risk_score', 5))))
        
        return {
            'ai_summary': result.get('ai_summary', f'Analysis of {title}')[:1000],
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_reason': result.get('risk_reason', 'Automated assessment')[:500]
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        # Fallback with basic keyword analysis
        return generate_fallback_analysis(title, content)
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return generate_fallback_analysis(title, content)


def generate_fallback_analysis(title, content):
    """
    Fast keyword-based fallback analysis when AI fails
    """
    text = (title + " " + content).lower()
    
    # Quick keyword-based risk assessment
    critical_keywords = ['zero-day', 'critical vulnerability', 'ransomware attack', 'data breach', 'widespread']
    high_keywords = ['vulnerability', 'exploit', 'malware', 'breach', 'attack', 'compromised']
    medium_keywords = ['patch', 'update', 'security', 'threat', 'warning']
    
    if any(kw in text for kw in critical_keywords):
        risk_level, risk_score = 'critical', 9
    elif any(kw in text for kw in high_keywords):
        risk_level, risk_score = 'high', 7
    elif any(kw in text for kw in medium_keywords):
        risk_level, risk_score = 'medium', 5
    else:
        risk_level, risk_score = 'low', 3
    
    return {
        'ai_summary': f"Cybersecurity news: {title}. AI analysis temporarily unavailable.",
        'risk_level': risk_level,
        'risk_score': risk_score,
        'risk_reason': f'Keyword-based assessment: {risk_level} priority security news.'
    }


def process_single_news_item(news_item):
    """
    Process a single news item - STREAMLINED
    """
    try:
        # Skip if already processed
        if news_item.processed_by_llm:
            return {'success': False, 'reason': 'already_processed'}
        
        # Skip if no URL
        if not news_item.url:
            news_item.processed_by_llm = True
            news_item.ai_summary = "No URL available."
            news_item.save()
            return {'success': False, 'reason': 'no_url'}
        
        # Extract content
        content = extract_article_content(news_item.url)
        
        if not content or len(content) < 100:
            # Use title/summary as fallback
            content = f"{news_item.title}. {news_item.summary}"
            logger.warning(f"Using title/summary fallback for {news_item.id}")
        
        news_item.content = content[:2000]  # Reduced storage
        
        # Generate AI analysis
        ai_result = generate_ai_summary_with_ollama(
            news_item.title,
            content,
            news_item.url
        )
        
        # Update database
        news_item.ai_summary = ai_result['ai_summary']
        news_item.risk_level = ai_result['risk_level']
        news_item.risk_score = ai_result['risk_score']
        news_item.risk_reason = ai_result['risk_reason']
        news_item.processed_by_llm = True
        news_item.processed_at = timezone.now()
        news_item.save()
        
        logger.info(f"✓ Processed {news_item.id}: {news_item.title[:50]}...")
        return {'success': True, 'id': news_item.id}
        
    except Exception as e:
        logger.error(f"Error processing {news_item.id}: {e}")
        news_item.ai_summary = "Processing error occurred."
        news_item.processed_by_llm = True
        news_item.save()
        return {'success': False, 'reason': str(e)}


def process_unprocessed_news(batch_size=10, delay=0.5, parallel=True, max_workers=4):
    """
    Process unprocessed news items - PARALLEL PROCESSING
    
    Args:
        batch_size: Number of items to process
        delay: Delay between batches (not per item)
        parallel: Use parallel processing
        max_workers: Number of parallel workers
    """
    unprocessed = NewsItem.objects.filter(processed_by_llm=False)[:batch_size]
    total = len(unprocessed)
    
    if total == 0:
        logger.info("No unprocessed news items found")
        return {'total': 0, 'processed': 0, 'failed': 0, 'skipped': 0}
    
    logger.info(f"Processing {total} news items (parallel={parallel}, workers={max_workers})")
    
    results = {
        'total': total,
        'processed': 0,
        'failed': 0,
        'skipped': 0
    }
    
    start_time = time.time()
    
    if parallel and total > 1:
        # PARALLEL PROCESSING for significant speedup
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(process_single_news_item, item): item 
                for item in unprocessed
            }
            
            for future in as_completed(future_to_item):
                result = future.result()
                if result['success']:
                    results['processed'] += 1
                elif result.get('reason') in ['already_processed', 'no_url']:
                    results['skipped'] += 1
                else:
                    results['failed'] += 1
    else:
        # SEQUENTIAL PROCESSING (fallback)
        for item in unprocessed:
            result = process_single_news_item(item)
            if result['success']:
                results['processed'] += 1
            elif result.get('reason') in ['already_processed', 'no_url']:
                results['skipped'] += 1
            else:
                results['failed'] += 1
            
            time.sleep(delay)
    
    elapsed = time.time() - start_time
    logger.info(
        f"✅ Complete in {elapsed:.1f}s: "
        f"{results['processed']} processed, "
        f"{results['failed']} failed, "
        f"{results['skipped']} skipped"
    )
    
    return results


def process_high_priority_first(batch_size=20, max_workers=4):
    """
    Process high-priority news first (priority >= 5)
    """
    # Get high-priority unprocessed items first
    high_priority = NewsItem.objects.filter(
        processed_by_llm=False,
        priority__gte=5
    ).order_by('-priority', '-created_at')[:batch_size]
    
    if high_priority.exists():
        logger.info(f"Processing {len(high_priority)} high-priority items first")
        return process_unprocessed_news(
            batch_size=len(high_priority),
            parallel=True,
            max_workers=max_workers
        )
    
    # If no high-priority, process regular items
    return process_unprocessed_news(
        batch_size=batch_size,
        parallel=True,
        max_workers=max_workers
    )


def reprocess_news_item(news_id):
    """
    Reprocess a specific news item by ID
    """
    try:
        news_item = NewsItem.objects.get(id=news_id)
        news_item.processed_by_llm = False
        news_item.save()
        
        result = process_single_news_item(news_item)
        return result['success']
    except NewsItem.DoesNotExist:
        logger.error(f"News item {news_id} not found")
        return False


def batch_reprocess_by_risk(risk_level='low', limit=10):
    """
    Reprocess items of a specific risk level (useful for improving low-quality analyses)
    """
    items = NewsItem.objects.filter(
        processed_by_llm=True,
        risk_level=risk_level
    )[:limit]
    
    for item in items:
        item.processed_by_llm = False
        item.save()
    
    return process_unprocessed_news(batch_size=limit, parallel=True)


def clear_content_cache():
    """
    Clear the content extraction cache
    """
    global CONTENT_CACHE
    CONTENT_CACHE.clear()
    logger.info("Content cache cleared")