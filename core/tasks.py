# core/tasks.py
from celery import shared_task
from .scraper import extract_links, extract_article
from news.models import Article

@shared_task
def scrape_site(url):
    links = extract_links(url)

    for link in links:
        data = extract_article(link)

        # Save only if new
        obj, created = Article.objects.get_or_create(
            url=link, defaults={
                "title": data["title"],
                "content": data["content"],
                "authors": ", ".join(data.get("authors", [])),
                "publish_date": data.get("publish_date"),
            }
        )
