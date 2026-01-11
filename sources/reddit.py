"""
Reddit Scraper - Holt Posts von öffentlichen Subreddits via Playwright
"""

from dataclasses import dataclass
from datetime import datetime
from playwright.async_api import async_playwright, Page
import asyncio


@dataclass
class RedditPost:
    title: str
    author: str
    url: str
    score: str
    comments: str
    time_ago: str
    subreddit: str


async def scrape_subreddit(subreddit: str, max_posts: int = 20) -> list[RedditPost]:
    """
    Scraped die neuesten Posts eines Subreddits.
    Nutzt die old.reddit.com Ansicht für einfacheres Parsing.
    """
    posts = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        # Old Reddit ist einfacher zu scrapen
        url = f"https://old.reddit.com/r/{subreddit}/new/"
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector("div.thing", timeout=10000)
            
            # Posts extrahieren
            things = await page.query_selector_all("div.thing.link")
            
            for thing in things[:max_posts]:
                try:
                    # Titel und URL
                    title_elem = await thing.query_selector("a.title")
                    title = await title_elem.inner_text() if title_elem else "Kein Titel"
                    post_url = await title_elem.get_attribute("href") if title_elem else ""
                    
                    # Wenn relative URL, vollständig machen
                    if post_url and post_url.startswith("/"):
                        post_url = f"https://old.reddit.com{post_url}"
                    
                    # Autor
                    author_elem = await thing.query_selector("a.author")
                    author = await author_elem.inner_text() if author_elem else "[deleted]"
                    
                    # Score
                    score_elem = await thing.query_selector("div.score.unvoted")
                    score = await score_elem.get_attribute("title") if score_elem else "?"
                    
                    # Kommentare
                    comments_elem = await thing.query_selector("a.comments")
                    comments = await comments_elem.inner_text() if comments_elem else "0 comments"
                    
                    # Zeit
                    time_elem = await thing.query_selector("time")
                    time_ago = await time_elem.get_attribute("title") if time_elem else ""
                    
                    posts.append(RedditPost(
                        title=title,
                        author=author,
                        url=post_url,
                        score=score,
                        comments=comments,
                        time_ago=time_ago,
                        subreddit=subreddit
                    ))
                    
                except Exception as e:
                    # Einzelne Posts überspringen bei Fehlern
                    continue
                    
        except Exception as e:
            print(f"Fehler beim Scrapen von r/{subreddit}: {e}")
        finally:
            await browser.close()
    
    return posts


def format_posts_for_llm(posts: list[RedditPost]) -> str:
    """Formatiert Posts für die LLM-Zusammenfassung."""
    if not posts:
        return "Keine Posts gefunden."
    
    # Gruppiere nach Subreddit für bessere Übersicht
    subreddits = set(p.subreddit for p in posts)
    lines = [f"# Reddit Posts aus {len(subreddits)} Subreddits\n"]
    
    for i, post in enumerate(posts, 1):
        lines.append(f"""
## {i}. r/{post.subreddit}: {post.title}
- **Autor:** u/{post.author}
- **Score:** {post.score} | **Kommentare:** {post.comments}
- **Link:** {post.url}
""")
    
    return "\n".join(lines)


# Test
if __name__ == "__main__":
    async def test():
        posts = await scrape_subreddit("ClaudeAI", max_posts=5)
        print(format_posts_for_llm(posts))
    
    asyncio.run(test())

