"""
LinkedIn Scraper - Holt Posts von der Timeline via Playwright mit Login
Nutzt persistentes Browser-Profil um Security-Checks zu minimieren.
"""

from dataclasses import dataclass
from playwright.async_api import async_playwright, Page
import asyncio
from pathlib import Path


@dataclass
class LinkedInPost:
    author: str
    author_headline: str
    content: str
    time_ago: str
    reactions: str
    comments: str
    url: str


# Persistentes Browser-Profil (speichert alles: Cookies, LocalStorage, Cache, etc.)
BROWSER_PROFILE_PATH = Path(__file__).parent.parent / ".linkedin_browser_profile"


async def login_linkedin(page: Page, email: str, password: str) -> bool:
    """Führt LinkedIn Login durch."""
    try:
        await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        
        # Warte auf Login-Form
        await page.wait_for_selector("#username", timeout=10000)
        
        # Menschlichere Eingabe mit kleinen Delays
        await page.fill("#username", email)
        await asyncio.sleep(0.5)
        await page.fill("#password", password)
        await asyncio.sleep(0.3)
        
        # Submit
        await page.click('button[type="submit"]')
        
        # Warte auf erfolgreichen Login (Feed oder Security Check)
        try:
            await page.wait_for_url("**/feed/**", timeout=30000)
            return True
        except:
            # Eventuell Security Verification nötig
            current_url = page.url
            if "checkpoint" in current_url or "security" in current_url or "challenge" in current_url:
                print("⚠️  LinkedIn Security Check erkannt!")
                print("   Bitte bestätige im geöffneten Browser und warte...")
                print("   (Das Fenster bleibt 60 Sekunden offen)")
                # Längere Wartezeit für manuelle Bestätigung
                for i in range(60):
                    await asyncio.sleep(1)
                    if "feed" in page.url:
                        print("   ✓ Verifizierung erfolgreich!")
                        return True
                return "feed" in page.url
            return False
            
    except Exception as e:
        print(f"Login-Fehler: {e}")
        return False


async def scrape_linkedin_feed(email: str, password: str, max_posts: int = 20) -> list[LinkedInPost]:
    """
    Scraped die LinkedIn Timeline/Feed.
    Nutzt persistentes Browser-Profil für vertrauenswürdigere Sessions.
    """
    posts = []
    
    # Stelle sicher, dass der Profilordner existiert
    BROWSER_PROFILE_PATH.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        # Persistenter Browser-Context - speichert ALLES wie ein echter Browser
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_PATH),
            headless=False,  # LinkedIn erkennt Headless-Browser
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="de-DE",
            timezone_id="Europe/Berlin",
        )
        
        # Seite im persistenten Context
        page = context.pages[0] if context.pages else await context.new_page()
        
        try:
            # Prüfe ob bereits eingeloggt
            await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
            await asyncio.sleep(3)
            
            # Cookie-Banner schließen falls vorhanden
            try:
                accept_btn = await page.query_selector("button[action-type='ACCEPT'], button:has-text('Accept'), button:has-text('Akzeptieren')")
                if accept_btn:
                    await accept_btn.click()
                    print("   → Cookie-Banner akzeptiert")
                    await asyncio.sleep(2)
            except:
                pass
            
            # Falls nicht eingeloggt, Login durchführen
            if "login" in page.url.lower() or "authwall" in page.url.lower():
                print("   → Login erforderlich...")
                logged_in = await login_linkedin(page, email, password)
                if not logged_in:
                    print("❌ LinkedIn Login fehlgeschlagen")
                    await context.close()
                    return []
            else:
                print("   → Bereits eingeloggt (Session wiederverwendet)")
            
            # Nochmal Cookie-Banner prüfen nach Login
            try:
                accept_btn = await page.query_selector("button[action-type='ACCEPT'], button:has-text('Accept'), button:has-text('Akzeptieren')")
                if accept_btn:
                    await accept_btn.click()
                    print("   → Cookie-Banner akzeptiert")
                    await asyncio.sleep(2)
            except:
                pass
            
            # Warte auf Feed-Content mit mehreren möglichen Selektoren
            feed_loaded = False
            for selector in ["div.feed-shared-update-v2", "[data-urn*='activity']", "main article", ".scaffold-finite-scroll"]:
                try:
                    await page.wait_for_selector(selector, timeout=8000)
                    feed_loaded = True
                    print(f"   → Feed geladen (Selector: {selector})")
                    break
                except:
                    continue
            
            if not feed_loaded:
                print("   ⚠️ Feed-Elemente nicht gefunden, versuche trotzdem zu scrapen...")
            
            # Scrolle um mehr Posts zu laden (menschlicher mit variablen Delays)
            for i in range(4):
                await page.evaluate("window.scrollBy(0, 600)")
                await asyncio.sleep(1.5)
            
            # Posts extrahieren mit verschiedenen Selektoren
            post_elements = await page.query_selector_all("div.feed-shared-update-v2")
            if not post_elements:
                post_elements = await page.query_selector_all("[data-urn*='activity']")
            if not post_elements:
                post_elements = await page.query_selector_all("main article")
            
            for elem in post_elements[:max_posts]:
                try:
                    # Autor
                    author_elem = await elem.query_selector("span.update-components-actor__name span[aria-hidden='true']")
                    author = await author_elem.inner_text() if author_elem else "Unbekannt"
                    author = author.strip()
                    
                    # Author Headline
                    headline_elem = await elem.query_selector("span.update-components-actor__description")
                    headline = await headline_elem.inner_text() if headline_elem else ""
                    headline = headline.strip().split('\n')[0] if headline else ""
                    
                    # Content
                    content_elem = await elem.query_selector("div.feed-shared-update-v2__description")
                    if not content_elem:
                        content_elem = await elem.query_selector("span.break-words")
                    content = await content_elem.inner_text() if content_elem else ""
                    content = content.strip()[:500]  # Begrenzen
                    
                    # Zeit
                    time_elem = await elem.query_selector("span.update-components-actor__sub-description")
                    time_ago = await time_elem.inner_text() if time_elem else ""
                    time_ago = time_ago.strip().split('•')[0].strip() if time_ago else ""
                    
                    # Reactions (grob)
                    reactions_elem = await elem.query_selector("span.social-details-social-counts__reactions-count")
                    reactions = await reactions_elem.inner_text() if reactions_elem else "0"
                    
                    # Comments
                    comments_elem = await elem.query_selector("button[aria-label*='comment']")
                    comments = "0"
                    if comments_elem:
                        comments_text = await comments_elem.inner_text()
                        comments = comments_text.strip() if comments_text else "0"
                    
                    # URL zum Post
                    urn_attr = await elem.get_attribute("data-urn")
                    url = f"https://www.linkedin.com/feed/update/{urn_attr}/" if urn_attr else ""
                    
                    if content:  # Nur Posts mit Content
                        posts.append(LinkedInPost(
                            author=author,
                            author_headline=headline,
                            content=content,
                            time_ago=time_ago,
                            reactions=reactions,
                            comments=comments,
                            url=url
                        ))
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Fehler beim Scrapen des LinkedIn Feeds: {e}")
        finally:
            await context.close()
    
    return posts


def format_posts_for_llm(posts: list[LinkedInPost]) -> str:
    """Formatiert Posts für die LLM-Zusammenfassung."""
    if not posts:
        return "Keine LinkedIn Posts gefunden."
    
    lines = ["# LinkedIn Feed Posts\n"]
    lines.append("WICHTIG: Nutze die Post-URLs in deiner Zusammenfassung als Quellenlinks!\n")
    
    for i, post in enumerate(posts, 1):
        lines.append(f"""
## Post #{i}: {post.author}
- **Position:** {post.author_headline}
- **Zeit:** {post.time_ago}
- **Reaktionen:** {post.reactions} | **Kommentare:** {post.comments}
- **POST-URL:** {post.url}

**Inhalt:**
{post.content}

---
""")
    
    return "\n".join(lines)


# Test
if __name__ == "__main__":
    async def test():
        # Ersetze mit echten Credentials zum Testen
        posts = await scrape_linkedin_feed("test@email.com", "password", max_posts=5)
        print(format_posts_for_llm(posts))
    
    asyncio.run(test())
