import requests
import random
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
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

CRAWL_DELAY = 5

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


def is_allowed_by_robots(url):
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
        selectors = [
            "h1 a",
            "h2 a",
            "h3 a",
            ".headline a",
            ".post-title a",
            ".entry-title a",
            ".story-title a",
            ".article-title a",
            "article h2 a",
            "header h1 a",
        ]

        headlines = []
        for sel in selectors:
            for tag in soup.select(sel):
                text = tag.get_text(strip=True)
                link = tag.get("href")
                if link and link.startswith("/"):
                    link = urljoin(url, link)
                if text:
                    headlines.append({"title": text, "url": link})

        return headlines[:10]
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return []


def save_to_db(news_map):
    created_items = []

    for site, items in news_map.items():
        for item in items:
            obj = NewsItem.objects.create(
                title=item["title"],
                summary=item["title"],
                content="",
                source=site,
                url=item["url"],
                priority=1,
            )
            created_items.append(obj)

    return created_items




def run_scraper():
    results = {}

    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(scrape_site, url): url for url in URLS}

        for future in as_completed(future_map):
            site = future_map[future]
            try:
                results[site] = future.result()
            except Exception as e:
                print(f"Error scraping {site}: {e}")
                results[site] = []

    return results
