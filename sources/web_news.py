"""
Generischer Web News Scraper
Unterstützt verschiedene News-Websites mit konfigurierbaren Selektoren
"""

from dataclasses import dataclass
from playwright.async_api import async_playwright
import asyncio
from typing import Optional


@dataclass
class WebArticle:
    title: str
    author: str
    excerpt: str
    content: str
    url: str
    source: str


# Vordefinierte Selektoren für bekannte Websites
SITE_CONFIGS = {
    "theverge": {
        "name": "The Verge",
        "base_url": "https://www.theverge.com/ai-artificial-intelligence",
        "article_links": "a[href*='/202']",  # /2024, /2025, /2026
        "title": "h1",
        "author": "a[href*='/authors/'], [class*='author']",
        "content": "article p, .article-body p, [class*='article-body'] p",
        "exclude_patterns": ["/authors/", "/archives/", "/about/", "/reviews/"]
    },
    "techcrunch": {
        "name": "TechCrunch",
        "base_url": "https://techcrunch.com/tag/artificial-intelligence/",
        "article_links": "article a[href*='/202'], h2 a[href*='/202'], h3 a[href*='/202']",
        "title": "h1",
        "author": "a[href*='/author/'], [class*='author']",
        "content": "article p, .article-content p, [class*='article'] p",
        "exclude_patterns": ["/author/", "/tag/", "/category/", "/event/"]
    },
    "mit_news": {
        "name": "MIT News",
        "base_url": "https://news.mit.edu/topic/artificial-intelligence2",
        "article_links": "a[href*='/202']",  # Relative URLs wie /2026/...
        "title": "h1",
        "author": ".publication-date, .author, [class*='author']",
        "content": "article p, .news-article p, [class*='article'] p, .paragraph p",
        "exclude_patterns": ["/topic/", "/office/"]
    },
    "ai_news": {
        "name": "AI News",
        "base_url": "https://www.artificialintelligence-news.com/",
        "article_links": "a[href*='/news/']",
        "title": "h1",
        "author": ".author, [class*='author'], .byline",
        "content": "article p, .entry-content p, .post-content p, [class*='content'] p",
        "exclude_patterns": ["/categories/", "/tag/", "/page/", "/author/", "/videos"]
    },
    "deutsche_startups": {
        "name": "Deutsche Startups",
        "base_url": "https://www.deutsche-startups.de/",  # Hauptseite statt Tag
        "article_links": "a[href*='deutsche-startups.de/202']",
        "title": "h1",
        "author": ".author, [class*='author'], .entry-meta a",
        "content": "article p, .entry-content p",
        "exclude_patterns": ["/tag/", "/kategorie/", "/page/"]
    }
}


async def scrape_web_source(source_key: str, max_articles: int = 5) -> list[WebArticle]:
    """
    Scraped Artikel von einer konfigurierten Web-Quelle.
    """
    if source_key not in SITE_CONFIGS:
        print(f"❌ Unbekannte Quelle: {source_key}")
        return []
    
    config = SITE_CONFIGS[source_key]
    articles = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # Übersichtsseite laden
            await page.goto(config["base_url"], wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # Artikel-Links sammeln
            article_links = []
            link_elements = await page.query_selector_all(config["article_links"])
            
            seen_urls = set()
            for elem in link_elements:
                href = await elem.get_attribute("href")
                if not href:
                    continue
                    
                # Vollständige URL sicherstellen
                if href.startswith("/"):
                    # Base domain extrahieren
                    from urllib.parse import urlparse
                    parsed = urlparse(config["base_url"])
                    href = f"{parsed.scheme}://{parsed.netloc}{href}"
                
                # Duplikate und Exclude-Patterns filtern
                if href in seen_urls:
                    continue
                
                skip = False
                for pattern in config.get("exclude_patterns", []):
                    if pattern in href:
                        skip = True
                        break
                
                if not skip and href not in seen_urls:
                    seen_urls.add(href)
                    article_links.append(href)
                    if len(article_links) >= max_articles:
                        break
            
            # Jeden Artikel besuchen
            for url in article_links[:max_articles]:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(1)
                    
                    # Titel
                    title_elem = await page.query_selector(config["title"])
                    title = await title_elem.inner_text() if title_elem else "Kein Titel"
                    
                    # Autor
                    author = config["name"]  # Fallback
                    author_elem = await page.query_selector(config["author"])
                    if author_elem:
                        author_text = await author_elem.inner_text()
                        if author_text and len(author_text) < 100:
                            author = author_text.strip()
                    
                    # Content
                    content_parts = []
                    content_elems = await page.query_selector_all(config["content"])
                    for elem in content_elems[:12]:  # Erste 12 Absätze
                        text = await elem.inner_text()
                        if text and len(text) > 30:
                            content_parts.append(text.strip())
                    
                    content = "\n\n".join(content_parts)
                    excerpt = content[:300] + "..." if len(content) > 300 else content
                    
                    if title and content:
                        articles.append(WebArticle(
                            title=title.strip(),
                            author=author,
                            excerpt=excerpt,
                            content=content[:2000],  # Begrenzen
                            url=url,
                            source=config["name"]
                        ))
                        
                except Exception as e:
                    print(f"  Fehler bei {url}: {str(e)[:50]}")
                    continue
                    
        except Exception as e:
            print(f"Fehler beim Scrapen von {config['name']}: {e}")
        finally:
            await browser.close()
    
    return articles


def format_articles_for_llm(articles: list[WebArticle], source_name: str) -> str:
    """Formatiert Artikel für die LLM-Zusammenfassung."""
    if not articles:
        return f"Keine Artikel von {source_name} gefunden."
    
    lines = [f"# {source_name} News\n"]
    lines.append("WICHTIG: Nutze die Artikel-URLs in deiner Zusammenfassung als Quellenlinks!\n")
    
    for i, article in enumerate(articles, 1):
        lines.append(f"""
## Artikel #{i}: {article.title}
- **Autor:** {article.author}
- **Quelle:** {article.source}
- **ARTIKEL-URL:** {article.url}

**Inhalt:**
{article.content}

---
""")
    
    return "\n".join(lines)


# Test
if __name__ == "__main__":
    async def test():
        for source in ["theverge", "techcrunch"]:
            print(f"\n=== Testing {source} ===")
            articles = await scrape_web_source(source, max_articles=2)
            for a in articles:
                print(f"  - {a.title[:50]}...")
    
    asyncio.run(test())
