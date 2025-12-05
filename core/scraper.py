import requests
import random
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import sys
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
    "https://www.schneier.com",
]


# ---------------------------------------------------------
# ROBOTS.TXT CHECK
# ---------------------------------------------------------

def is_allowed_by_robots(url):
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        resp = requests.get(robots_url, headers=HEADERS, timeout=5)

        # No robots.txt → assume allowed
        if resp.status_code != 200:
            return True

        disallowed = []
        for line in resp.text.splitlines():
            line = line.strip()
            if line.startswith("Disallow:"):
                path = line.replace("Disallow:", "").strip()
                if path:
                    disallowed.append(path)

        # Check if URL path starts with any disallowed rule
        path = parsed.path
        for rule in disallowed:
            if path.startswith(rule):
                return False

        return True

    except Exception:
        return True  # fail-open fallback


# ---------------------------------------------------------
# SCRAPER LOGIC
# ---------------------------------------------------------

def scrape_site(url):
    if not is_allowed_by_robots(url):
        print(f"⛔ robots.txt disallows scraping: {url}")
        return []

    print(f"Scraping: {url}")

    # Respect crawl delay
    time.sleep(CRAWL_DELAY + random.uniform(0.5, 1.5))

    try:
        # Retry if blocked
        for attempt in range(3):
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code in [403, 429]:
                print(f"⚠️ Blocked ({resp.status_code}). Retrying in {2+attempt}s…")
                time.sleep(2 + attempt)
                continue
            break

        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        print(f"✅ Fetched {url} successfully.",soup.title.string if soup.title else 'No Title')
        # Multiple selectors for robustness
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

                if text and text not in headlines:
                    headlines.append({"title": text, "url": link})

        return headlines[:10]

    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
        return []


# ---------------------------------------------------------
# OPTIONAL: SAVE TO DATABASE
# ---------------------------------------------------------

def save_to_db(news_map):
    for site, items in news_map.items():
        for item in items:
            NewsItem.objects.create(
                title=item["title"],
                summary=item["title"],
                content="",
                source=site,
                url=item["url"],
                priority=1,
            )


# ---------------------------------------------------------
# RUN ALL SCRAPERS
# ---------------------------------------------------------

def scrape_all_sites(urls):
    results = {}
    for url in urls:
        results[url] = scrape_site(url)
    return results


if __name__ == "__main__":
    news = scrape_all_sites(URLS)

    for site, headlines in news.items():
        print("\n" + "=" * 80)
        print(f"🔐 {site}")
        print("=" * 80)
        for h in headlines:
            print(f"• {h['title']}  -> {h['url']}")

    # 🔥 OPTIONAL: Enable only if you want DB saving
    print("News.....",news)
    save_to_db(news)
