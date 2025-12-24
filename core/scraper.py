# core/scraper.py - FIXED VERSION (Cybersecurity news only)

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
from django.utils import timezone
 
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

# ONLY cybersecurity-focused sites
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

# STRICT cybersecurity keywords - must contain at least one
REQUIRED_CYBERSECURITY_KEYWORDS = [
    # Threats & Attacks
    'vulnerability', 'exploit', 'breach', 'hack', 'malware', 'ransomware',
    'phishing', 'attack', 'threat', 'cybersecurity', 'cyber security',
    'zero-day', '0-day', 'backdoor', 'trojan', 'virus', 'worm',
    
    # Security Operations
    'patch', 'security update', 'critical update', 'security advisory',
    'cve-', 'security flaw', 'security bug', 'security issue',
    
    # Incidents
    'data breach', 'data leak', 'compromised', 'hacked', 'attacked',
    'incident', 'security breach', 'cyber attack', 'cyberattack',
    
    # Threat Actors
    'apt', 'threat actor', 'hacker group', 'nation-state',
    
    # Security Tools/Concepts
    'firewall', 'antivirus', 'endpoint security', 'network security',
    'encryption', 'authentication', 'credential', 'password'
]

# Topics to EXCLUDE (AI, general tech, etc.)
EXCLUDE_KEYWORDS = [
    'agentic commerce', 'digital transformation', 'ai-enabled',
    'machine learning', 'artificial intelligence', 'chatgpt',
    'generative ai', 'llm', 'large language model',
    # Unless they're about AI security vulnerabilities
]

# High priority cybersecurity keywords
HIGH_PRIORITY_KEYWORDS = [
    'breach', 'vulnerability', 'zero-day', 'exploit', 'ransomware',
    'malware', 'attack', 'threat', 'critical', 'emergency',
    'patch', 'compromise', 'leaked', 'hacked', 'data breach',
    'security flaw', 'cyber attack', 'apt', 'threat actor'
]

def make_aware_if_needed(dt):
    """Convert naive datetime to timezone-aware"""
    if dt and timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt

def is_cybersecurity_news(title: str, summary: str = "") -> bool:
    """
    Strictly check if article is cybersecurity-related
    Must contain at least one required keyword
    """
    text = (title + " " + summary).lower()
    
    # Must contain at least one cybersecurity keyword
    has_cyber_keyword = any(keyword in text for keyword in REQUIRED_CYBERSECURITY_KEYWORDS)
    
    if not has_cyber_keyword:
        return False
    
    # Check if it's about AI/general tech WITHOUT security context
    for exclude_kw in EXCLUDE_KEYWORDS:
        if exclude_kw in text:
            # Allow if it mentions security/vulnerability alongside AI
            if not any(sec_kw in text for sec_kw in ['security', 'vulnerability', 'breach', 'attack', 'threat']):
                return False
    
    return True


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
        return now
    
    if 'today' in text or 'just now' in text:
        return now
    
    if 'yesterday' in text:
        return now - timedelta(days=1)
    
    # Try to parse actual dates
    date_patterns = [
        r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})',
        r'(\d{1,2})\s+(\w{3})\s+(\d{4})',
        r'(\d{4})-(\d{2})-(\d{2})',
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
        return True
    
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
    """Scrape a single site for recent cybersecurity news"""
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
        
        # Enhanced selectors
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
        
        # Try to find complete article blocks
        for selector in article_selectors:
            for article in soup.select(selector):
                title_tag = article.select_one('h1 a, h2 a, h3 a, a[class*="title"]')
                if not title_tag:
                    continue
                
                title = title_tag.get_text(strip=True)
                link = title_tag.get('href')
                
                if link and link.startswith('/'):
                    link = urljoin(url, link)
                
                # Look for date
                date_tag = None
                for date_sel in date_selectors:
                    date_tag = article.select_one(date_sel)
                    if date_tag:
                        break
                
                date_text = date_tag.get_text(strip=True) if date_tag else None
                datetime_attr = date_tag.get('datetime') if date_tag else None
                
                article_date = extract_date_from_text(datetime_attr or date_text or '')
                
                # Look for summary
                summary_tag = article.select_one('.excerpt, .summary, .description, p')
                summary = summary_tag.get_text(strip=True) if summary_tag else title
                
                if title and link:
                    articles.append({
                        'title': title,
                        'url': link,
                        'date': article_date,
                        'summary': summary,
                    })
        
        # Fallback: simple headline extraction
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
                        })
        
        # STRICT FILTERING: Only cybersecurity news
        cyber_articles = []
        for art in articles:
            if is_cybersecurity_news(art['title'], art.get('summary', '')):
                if is_within_timeframe(art.get('date')):
                    art['is_priority'] = is_high_priority(art['title'], art.get('summary', ''))
                    cyber_articles.append(art)
        
        # Sort by priority and date
        cyber_articles.sort(
            key=lambda x: (not x['is_priority'], x['date'] or datetime.min),
            reverse=True
        )
        
        # Return top articles
        result = cyber_articles[:MAX_ARTICLES_PER_SITE]
        
        print(f"✓ {url}: Found {len(result)} cybersecurity articles ({sum(1 for a in result if a['is_priority'])} high-priority)")
        
        return result
        
    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
        return []
def fetch_full_article_content(article_url):
    """Fetch and extract full article content from article page"""
    try:
        resp = requests.get(article_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove unwanted tags
        for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'form']):
            tag.decompose()

        # Common article body selectors (covers most news sites)
        content_selectors = [
            'article',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.story-content',
            '.content',
            '#content',
            'main',
        ]

        article_body = None
        for selector in content_selectors:
            article_body = soup.select_one(selector)
            if article_body:
                break

        if not article_body:
            return ""

        paragraphs = []
        for p in article_body.find_all('p'):
            text = p.get_text(strip=True)
            if len(text) > 50:  # ignore junk lines
                paragraphs.append(text)

        return "\n\n".join(paragraphs)

    except Exception as e:
        print(f"⚠️ Failed to fetch full content: {article_url} | {e}")
        return ""

def fetch_article_publish_date(article_url):
    """Extract publish date from article page"""
    try:
        resp = requests.get(article_url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # 1. <time datetime="...">
        time_tag = soup.find("time")
        if time_tag:
            datetime_val = time_tag.get("datetime") or time_tag.get_text(strip=True)
            date = extract_date_from_text(datetime_val)
            if date:
                return date

        # 2. Meta tags (most reliable)
        meta_props = [
            {"property": "article:published_time"},
            {"name": "pubdate"},
            {"name": "publish-date"},
            {"name": "date"},
        ]

        for prop in meta_props:
            meta = soup.find("meta", prop)
            if meta and meta.get("content"):
                date = extract_date_from_text(meta["content"])
                if date:
                    return date

        # 3. Visible date text fallback
        date_selectors = [
            '.date', '.published', '.post-date',
            '.entry-date', '.timestamp',
            'span[class*="date"]',
            'div[class*="date"]',
        ]

        for selector in date_selectors:
            tag = soup.select_one(selector)
            if tag:
                date = extract_date_from_text(tag.get_text(strip=True))
                if date:
                    return make_aware_if_needed(date)


    except Exception as e:
        print(f"⚠️ Publish date fetch failed: {article_url} | {e}")

    return None

def save_to_db(news_map):
    created_items = []
    duplicate_count = 0
    non_cyber_count = 0
    
    for site, items in news_map.items():
        for item in items:
            # Double-check cybersecurity relevance
            if not is_cybersecurity_news(item['title'], item.get('summary', '')):
                non_cyber_count += 1
                continue
            
            # Check for duplicates
            existing = NewsItem.objects.filter(
                url=item['url']
            ).first() or NewsItem.objects.filter(
                title=item['title'],
                source=site
            ).first()
            
            if existing:
                duplicate_count += 1
                continue
            
            # Set priority
            priority = 5 if item.get('is_priority') else 1

            # 🔥 NEW: fetch full article data
            full_content = fetch_full_article_content(item['url'])
            publish_date = fetch_article_publish_date(item['url'])

            if not publish_date:
                publish_date = item.get('date')

            # 🔥 FIX: make timezone-aware
            publish_date = make_aware_if_needed(publish_date)

            obj = NewsItem.objects.create(
                title=item['title'],
                summary=item.get('summary', item['title']),
                content=full_content[:80000],  # safety limit
                source=site,
                url=item['url'],
                priority=priority,
                published_date=publish_date,
            )

            created_items.append(obj)

    print(f"\n📊 Summary: {len(created_items)} new articles saved")
    print(f"   Duplicates skipped: {duplicate_count}")

    return created_items



def run_scraper():
    """Run scraper across all configured sites"""
    print(f"\n🔍 Starting cybersecurity news scraper (last {HOURS_LOOKBACK} hours)...\n")
    
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
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
    print(f"   Total cybersecurity articles: {total_articles}")
    print(f"   High-priority: {high_priority_count}")
    
    return results


if __name__ == "__main__":
    scraped_data = run_scraper()
    saved_items = save_to_db(scraped_data)
    print(f"\n✅ Saved {len(saved_items)} new cybersecurity articles to database")