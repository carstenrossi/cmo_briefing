"""
Futurism.com AI News Scraper
Holt die neuesten AI-Artikel von futurism.com/category/artificial-intelligence
"""

from dataclasses import dataclass
from playwright.async_api import async_playwright
import asyncio


@dataclass
class FuturismArticle:
    title: str
    author: str
    category: str
    excerpt: str
    content: str
    url: str


async def scrape_futurism(max_articles: int = 5) -> list[FuturismArticle]:
    """
    Scraped die neuesten AI-Artikel von Futurism.com.
    Geht auf jeden Artikel und holt den vollen Inhalt.
    """
    articles = []
    base_url = "https://futurism.com/category/artificial-intelligence"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # Übersichtsseite laden
            await page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # Artikel-Links sammeln
            article_links = []
            
            # Die Artikel-Cards finden
            cards = await page.query_selector_all("article a[href*='/'], .post-card a[href*='/']")
            
            # Alternative Selektoren falls die ersten nicht funktionieren
            if not cards:
                cards = await page.query_selector_all("a[href*='futurism.com/']")
            
            seen_urls = set()
            for card in cards:
                href = await card.get_attribute("href")
                if href and "/category/" not in href and href not in seen_urls:
                    # Vollständige URL sicherstellen
                    if href.startswith("/"):
                        href = f"https://futurism.com{href}"
                    if "futurism.com" in href and "/category/" not in href and "/tag/" not in href:
                        seen_urls.add(href)
                        article_links.append(href)
                        if len(article_links) >= max_articles:
                            break
            
            # Jeden Artikel besuchen und Inhalt extrahieren
            for url in article_links[:max_articles]:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(1)
                    
                    # Titel
                    title_elem = await page.query_selector("h1")
                    title = await title_elem.inner_text() if title_elem else "Kein Titel"
                    
                    # Autor
                    author_elem = await page.query_selector("a[rel='author'], .author-name, [class*='author']")
                    author = await author_elem.inner_text() if author_elem else "Futurism"
                    
                    # Kategorie
                    category_elem = await page.query_selector("a[href*='/category/'] span, .category")
                    category = await category_elem.inner_text() if category_elem else "AI"
                    
                    # Artikel-Content
                    content_elem = await page.query_selector("article, .article-content, .post-content, [class*='article-body']")
                    if content_elem:
                        # Paragraphen extrahieren
                        paragraphs = await content_elem.query_selector_all("p")
                        content_parts = []
                        for p in paragraphs[:10]:  # Erste 10 Absätze
                            text = await p.inner_text()
                            if text and len(text) > 20:  # Nur substantielle Absätze
                                content_parts.append(text)
                        content = "\n\n".join(content_parts)
                    else:
                        content = ""
                    
                    # Excerpt (erste 200 Zeichen des Contents)
                    excerpt = content[:300] + "..." if len(content) > 300 else content
                    
                    if title and content:
                        articles.append(FuturismArticle(
                            title=title.strip(),
                            author=author.strip(),
                            category=category.strip(),
                            excerpt=excerpt,
                            content=content[:1500],  # Begrenzen für Token-Effizienz
                            url=url
                        ))
                        
                except Exception as e:
                    print(f"  Fehler bei Artikel {url}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Fehler beim Scrapen von Futurism: {e}")
        finally:
            await browser.close()
    
    return articles


def format_posts_for_llm(articles: list[FuturismArticle]) -> str:
    """Formatiert Artikel für die LLM-Zusammenfassung."""
    if not articles:
        return "Keine Futurism-Artikel gefunden."
    
    lines = ["# Futurism.com AI News\n"]
    lines.append("WICHTIG: Nutze die Artikel-URLs in deiner Zusammenfassung als Quellenlinks!\n")
    
    for i, article in enumerate(articles, 1):
        lines.append(f"""
## Artikel #{i}: {article.title}
- **Autor:** {article.author}
- **Kategorie:** {article.category}
- **ARTIKEL-URL:** {article.url}

**Inhalt:**
{article.content}

---
""")
    
    return "\n".join(lines)


# Test
if __name__ == "__main__":
    async def test():
        articles = await scrape_futurism(max_articles=3)
        print(format_posts_for_llm(articles))
    
    asyncio.run(test())

