"""
The Neuron Newsletter Scraper
Holt die neuesten Newsletter-Artikel von theneuron.ai
"""

from dataclasses import dataclass
from playwright.async_api import async_playwright
import asyncio


@dataclass
class NeuronArticle:
    title: str
    excerpt: str
    content: str
    url: str


async def scrape_theneuron(max_articles: int = 5) -> list[NeuronArticle]:
    """
    Scraped die neuesten Newsletter von The Neuron.
    """
    articles = []
    base_url = "https://www.theneuron.ai"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # Newsletter-Übersicht laden
            await page.goto(f"{base_url}/newsletter", wait_until="domcontentloaded", timeout=30000)
            
            # Warte auf JavaScript-Rendering
            await asyncio.sleep(4)
            
            # Artikel-Links sammeln (relative URLs /newsletter/...)
            article_links = []
            link_elements = await page.query_selector_all("a[href^='/newsletter/']")
            
            seen_urls = set()
            for elem in link_elements:
                href = await elem.get_attribute("href")
                if href and href not in seen_urls and href != "/newsletter":
                    full_url = f"{base_url}{href}"
                    seen_urls.add(href)
                    article_links.append(full_url)
                    if len(article_links) >= max_articles:
                        break
            
            # Jeden Artikel besuchen
            for url in article_links[:max_articles]:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await asyncio.sleep(2)
                    
                    # Titel
                    title_elem = await page.query_selector("h1")
                    title = await title_elem.inner_text() if title_elem else "Kein Titel"
                    
                    # Content - verschiedene mögliche Container
                    content_parts = []
                    
                    # Versuche verschiedene Content-Selektoren
                    for selector in ["article p", "[class*='article'] p", "[class*='content'] p", ".newsletter-content p", "main p"]:
                        content_elems = await page.query_selector_all(selector)
                        if content_elems:
                            for elem in content_elems[:15]:
                                text = await elem.inner_text()
                                if text and len(text) > 30:
                                    content_parts.append(text.strip())
                            if content_parts:
                                break
                    
                    content = "\n\n".join(content_parts)
                    excerpt = content[:300] + "..." if len(content) > 300 else content
                    
                    if title and content:
                        articles.append(NeuronArticle(
                            title=title.strip(),
                            excerpt=excerpt,
                            content=content[:2000],
                            url=url
                        ))
                        
                except Exception as e:
                    print(f"  Fehler bei Artikel {url}: {str(e)[:50]}")
                    continue
                    
        except Exception as e:
            print(f"Fehler beim Scrapen von The Neuron: {e}")
        finally:
            await browser.close()
    
    return articles


def format_posts_for_llm(articles: list[NeuronArticle]) -> str:
    """Formatiert Artikel für die LLM-Zusammenfassung."""
    if not articles:
        return "Keine The Neuron Artikel gefunden."
    
    lines = ["# The Neuron Newsletter\n"]
    lines.append("WICHTIG: Nutze die Artikel-URLs in deiner Zusammenfassung als Quellenlinks!\n")
    
    for i, article in enumerate(articles, 1):
        lines.append(f"""
## Artikel #{i}: {article.title}
- **ARTIKEL-URL:** {article.url}

**Inhalt:**
{article.content}

---
""")
    
    return "\n".join(lines)


# Test
if __name__ == "__main__":
    async def test():
        articles = await scrape_theneuron(max_articles=3)
        print(f"Gefunden: {len(articles)} Artikel")
        for a in articles:
            print(f"  - {a.title[:60]}...")
    
    asyncio.run(test())
