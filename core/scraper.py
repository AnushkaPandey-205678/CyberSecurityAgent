import requests
import random
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import re
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cyberagent.settings")
import django
django.setup()
from core.models import NewsItem

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

CRAWL_DELAY = 3
MAX_ARTICLES_PER_SITE = 20
HOURS_LOOKBACK = 24

URLS = [
    "https://krebsonsecurity.com",
    "https://thehackernews.com",
    "https://www.darkreading.com",
    "https://www.bleepingcomputer.com",
    "https://www.securityweek.com",
    "https://www.csoonline.com",
    "https://www.zdnet.com/topic/security",
    "https://www.cyberscoop.com",
    "https://www.bankinfosecurity.com",
    "https://gbhackers.com",
    "https://www.schneier.com",
]

# Keywords that indicate high-priority cybersecurity news
HIGH_PRIORITY_KEYWORDS = [
    'breach', 'vulnerability', 'zero-day', 'exploit', 'ransomware',
    'malware', 'attack', 'threat', 'critical', 'emergency',
    'patch', 'compromise', 'leaked', 'hacked', 'data breach',
    'security flaw', 'cyber attack', 'apt', 'threat actor'
]


def is_high_priority(title, summary=""):
    """Check if article is high priority based on keywords"""
    text = (title + " " + summary).lower()
    return any(keyword in text for keyword in HIGH_PRIORITY_KEYWORDS)


def extract_date_from_text(text):
    """Try to extract date from various text formats"""
    if not text:
        return None
    
    text = text.lower().strip()
    now = datetime.now()
    
    # Check for relative dates
    if 'hour' in text or 'hr' in text:
        hours_match = re.search(r'(\d+)\s*(?:hour|hr)', text)
        if hours_match:
            hours = int(hours_match.group(1))
            return now - timedelta(hours=hours)
    
    if 'minute' in text or 'min' in text:
        return now  # Consider as today
    
    if 'today' in text or 'just now' in text:
        return now
    
    if 'yesterday' in text:
        return now - timedelta(days=1)
    
    # Try to parse actual dates (Dec 10, 2024, etc.)
    date_patterns = [
        r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})',  # Dec 10, 2024
        r'(\d{1,2})\s+(\w{3})\s+(\d{4})',     # 10 Dec 2024
        r'(\d{4})-(\d{2})-(\d{2})',           # 2024-12-10
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                date_str = match.group(0)
                for fmt in ['%b %d, %Y', '%d %b %Y', '%Y-%m-%d', '%B %d, %Y']:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except:
                        continue
            except:
                continue
    
    return None


def is_within_timeframe(article_date, hours=HOURS_LOOKBACK):
    """Check if article is within specified hours"""
    if not article_date:
        return True  # If we can't determine date, include it
    
    cutoff = datetime.now() - timedelta(hours=hours)
    return article_date >= cutoff


def is_allowed_by_robots(url):
    """Check robots.txt before scraping"""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    try:
        resp = requests.get(robots_url, headers=HEADERS, timeout=5)
        if resp.status_code != 200:
            return True
        
        disallowed = []
        for line in resp.text.splitlines():
            if line.startswith("Disallow:"):
                path = line.replace("Disallow:", "").strip()
                if path:
                    disallowed.append(path)
        
        path = parsed.path
        for rule in disallowed:
            if path.startswith(rule):
                return False
        return True
    except:
        return True


def scrape_site(url):
    """Scrape a single site for recent high-priority news"""
    if not is_allowed_by_robots(url):
        print(f"❌ Not allowed by robots.txt: {url}")
        return []
    
    time.sleep(CRAWL_DELAY + random.uniform(0.5, 1.5))
    
    try:
        for attempt in range(3):
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code in [403, 429]:
                time.sleep(2 + attempt)
                continue
            break
        
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Enhanced selectors for headlines and dates
        article_selectors = [
            'article',
            '.post',
            '.entry',
            '.story',
            '.news-item',
            '.article-item',
        ]
        
        headline_selectors = [
            'h1 a', 'h2 a', 'h3 a',
            '.headline a', '.post-title a', '.entry-title a',
            '.story-title a', '.article-title a',
            'article h2 a', 'header h1 a', 'header h2 a',
        ]
        
        date_selectors = [
            'time', '.date', '.post-date', '.published',
            '.entry-date', '.story-date', '.timestamp',
            'span[class*="date"]', 'span[class*="time"]',
        ]
        
        articles = []
        
        # First, try to find complete article blocks
        for selector in article_selectors:
            for article in soup.select(selector):
                title_tag = article.select_one('h1 a, h2 a, h3 a, a[class*="title"]')
                if not title_tag:
                    continue
                
                title = title_tag.get_text(strip=True)
                link = title_tag.get('href')
                
                if link and link.startswith('/'):
                    link = urljoin(url, link)
                
                # Look for date within the article
                date_tag = None
                for date_sel in date_selectors:
                    date_tag = article.select_one(date_sel)
                    if date_tag:
                        break
                
                date_text = date_tag.get_text(strip=True) if date_tag else None
                datetime_attr = date_tag.get('datetime') if date_tag else None
                
                article_date = extract_date_from_text(datetime_attr or date_text or '')
                
                # Look for summary/excerpt
                summary_tag = article.select_one('.excerpt, .summary, .description, p')
                summary = summary_tag.get_text(strip=True) if summary_tag else title
                
                if title and link:
                    articles.append({
                        'title': title,
                        'url': link,
                        'date': article_date,
                        'summary': summary,
                        'is_priority': is_high_priority(title, summary)
                    })
        
        # Fallback: simple headline extraction if article blocks not found
        if not articles:
            for selector in headline_selectors:
                for tag in soup.select(selector):
                    title = tag.get_text(strip=True)
                    link = tag.get('href')
                    
                    if link and link.startswith('/'):
                        link = urljoin(url, link)
                    
                    if title and link:
                        articles.append({
                            'title': title,
                            'url': link,
                            'date': None,
                            'summary': title,
                            'is_priority': is_high_priority(title)
                        })
        
        # Filter by date and priority
        recent_articles = [
            art for art in articles 
            if is_within_timeframe(art.get('date'))
        ]
        
        # Sort by priority first, then by date
        recent_articles.sort(
            key=lambda x: (not x['is_priority'], x['date'] or datetime.min),
            reverse=True
        )
        
        # Return top articles
        result = recent_articles[:MAX_ARTICLES_PER_SITE]
        
        print(f"✓ {url}: Found {len(result)} articles ({sum(1 for a in result if a['is_priority'])} high-priority)")
        
        return result
        
    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
        return []


def save_to_db(news_map):
    """Save scraped articles to database, avoiding duplicates"""
    created_items = []
    duplicate_count = 0
    
    for site, items in news_map.items():
        for item in items:
            # Check if article already exists (by URL or title)
            existing = NewsItem.objects.filter(
                url=item['url']
            ).first() or NewsItem.objects.filter(
                title=item['title'],
                source=site
            ).first()
            
            if existing:
                duplicate_count += 1
                continue
            
            # Set priority based on keywords
            priority = 5 if item.get('is_priority') else 1
            
            obj = NewsItem.objects.create(
                title=item['title'],
                summary=item.get('summary', item['title']),
                content='',
                source=site,
                url=item['url'],
                priority=priority,
            )
            created_items.append(obj)
    
    print(f"\n📊 Summary: {len(created_items)} new articles saved, {duplicate_count} duplicates skipped")
    return created_items


def run_scraper():
    """Run scraper across all configured sites"""
    print(f"\n🔍 Starting scraper (last {HOURS_LOOKBACK} hours, max {MAX_ARTICLES_PER_SITE} per site)...\n")
    
    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:  # Reduced workers to be more polite
        future_map = {executor.submit(scrape_site, url): url for url in URLS}
        
        for future in as_completed(future_map):
            site = future_map[future]
            try:
                results[site] = future.result()
            except Exception as e:
                print(f"❌ Error scraping {site}: {e}")
                results[site] = []
    
    # Calculate totals
    total_articles = sum(len(v) for v in results.values())
    high_priority_count = sum(
        sum(1 for item in articles if item.get('is_priority'))
        for articles in results.values()
    )
    
    print(f"\n✅ Scraping complete!")
    print(f"   Total articles: {total_articles}")
    print(f"   High-priority: {high_priority_count}")
    
    return results


if __name__ == "__main__":
    scraped_data = run_scraper()
    saved_items = save_to_db(scraped_data)
    print(f"\n✅ Saved {len(saved_items)} new articles to database")