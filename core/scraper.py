import requests
import random
import time
import re
import os
import sys
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
import trafilatura
from trafilatura import extract
from readability import Document
import justext

# ───────────────────────── Django setup ─────────────────────────
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cyberagent.settings")

import django
django.setup()

from core.models import NewsItem

# ───────────────────────── Config ─────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

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

CRAWL_DELAY = 2
HOURS_LOOKBACK = 48
MAX_ARTICLES_PER_SITE = 15
MAX_CONTENT_LENGTH = 50000

HIGH_PRIORITY_KEYWORDS = [
    "breach", "vulnerability", "zero-day", "exploit", "ransomware",
    "malware", "attack", "critical", "patched", "leak", "apt"
]

# ───────────────────────── Utilities ─────────────────────────
def is_high_priority(title, summary=""):
    text = f"{title} {summary}".lower()
    return any(k in text for k in HIGH_PRIORITY_KEYWORDS)

def is_allowed_by_robots(url):
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        r = requests.get(robots_url, headers=HEADERS, timeout=5)
        if r.status_code != 200:
            return True

        for line in r.text.splitlines():
            if line.lower().startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if parsed.path.startswith(path):
                    return False
        return True
    except:
        return True

def parse_date(text):
    if not text:
        return None

    patterns = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y-%m-%d"
    ]

    for p in patterns:
        try:
            return datetime.strptime(text.strip(), p)
        except:
            pass
    return None

def within_timeframe(dt):
    if not dt:
        return True
    return dt >= datetime.now() - timedelta(hours=HOURS_LOOKBACK)

# ───────────────────────── Content Extractor ─────────────────────────
class ContentExtractor:

    @staticmethod
    def extract_full_content(url, html=None):
        if not html:
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                r.raise_for_status()
                html = r.text
            except:
                return ""

        # Trafilatura
        content = extract(
            html, url=url,
            include_links=False,
            include_images=False,
            output_format="txt"
        )

        # Readability fallback
        if not content or len(content) < 500:
            try:
                doc = Document(html)
                soup = BeautifulSoup(doc.summary(), "html.parser")
                content = soup.get_text("\n", strip=True)
            except:
                content = None

        # jusText fallback
        if not content or len(content) < 500:
            try:
                paragraphs = justext.justext(html, justext.get_stoplist("English"))
                content = "\n\n".join(p.text for p in paragraphs if not p.is_boilerplate)
            except:
                content = None

        if not content:
            return ""

        content = re.sub(r"\n\s*\n", "\n\n", content).strip()
        return content[:MAX_CONTENT_LENGTH]

# ───────────────────────── Site Scraper ─────────────────────────
def scrape_site(site_url):
    print(f"🌐 Scraping {site_url}")
    if not is_allowed_by_robots(site_url):
        return []

    time.sleep(random.uniform(1, 2))

    try:
        r = requests.get(site_url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    articles = []

    for tag in soup.select("article h2 a, article h3 a, h2 a, h3 a"):
        title = tag.get_text(strip=True)
        link = tag.get("href")

        if not title or not link:
            continue

        if link.startswith("/"):
            link = urljoin(site_url, link)

        articles.append({
            "title": title,
            "url": link,
            "summary": title,
            "is_priority": is_high_priority(title)
        })

    return articles[:MAX_ARTICLES_PER_SITE]

# ───────────────────────── Article Scraper ─────────────────────────
def scrape_article(article):
    url = article["url"]

    if not is_allowed_by_robots(url):
        return None

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        html = r.text
    except:
        return None

    soup = BeautifulSoup(html, "html.parser")

    date = None
    meta = soup.select_one('meta[property="article:published_time"]')
    if meta:
        date = parse_date(meta.get("content"))

    content = ContentExtractor.extract_full_content(url, html)
    word_count = len(content.split())

    return {
        **article,
        "content": content,
        "word_count": word_count,
        "reading_time": max(1, word_count // 200),
        "date": date
    }

# ───────────────────────── Save to DB ─────────────────────────
def save_articles(site, articles):
    created = 0
    updated = 0

    for a in articles:
        obj = NewsItem.objects.filter(url=a["url"]).first()

        if obj:
            if a["content"] and not obj.content:
                obj.content = a["content"]
                obj.word_count = a["word_count"]
                obj.reading_time_minutes = a["reading_time"]
                obj.save()
                updated += 1
            continue

        NewsItem.objects.create(
            title=a["title"],
            summary=a["summary"][:500],
            content=a["content"],
            source=site,
            url=a["url"],
            priority=5 if a["is_priority"] else 1,
            word_count=a["word_count"],
            reading_time_minutes=a["reading_time"]
        )
        created += 1

    return created, updated

# ───────────────────────── Main Runner ─────────────────────────
def run():
    print("\n🚀 Starting Unified Cyber News Scraper\n")

    for site in URLS:
        articles = scrape_site(site)

        detailed = []
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(scrape_article, a) for a in articles]

            for f in as_completed(futures):
                res = f.result()
                if res and within_timeframe(res["date"]):
                    detailed.append(res)

        created, updated = save_articles(site, detailed)
        print(f"✅ {site}: {created} new | {updated} updated")

    print("\n🎉 Scraping completed successfully")

if __name__ == "__main__":
    run()
