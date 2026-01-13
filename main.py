#!/usr/bin/env python3
"""
🎙️ CMO Executive Briefing Generator
Sammelt KI-News und erstellt Podcast-Skripte für CMOs und Heads of Communications.

Usage:
    python main.py          # Erstellt das Executive Briefing
    python main.py --help   # Zeigt Hilfe
"""

import asyncio
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

import markdown
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from sources.reddit import scrape_subreddit, format_posts_for_llm as format_reddit
from sources.linkedin import scrape_linkedin_feed, format_posts_for_llm as format_linkedin
from sources.futurism import scrape_futurism, format_posts_for_llm as format_futurism
from sources.theneuron import scrape_theneuron, format_posts_for_llm as format_neuron
from sources.web_news import scrape_web_source, format_articles_for_llm, SITE_CONFIGS
from llm.summarizer import create_executive_briefing


console = Console()

# Konfiguration laden
CONFIG_PATH = Path(__file__).parent / "config.yaml"
OUTPUT_DIR = Path(__file__).parent / "output"


# HTML Template für das Executive Briefing
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎙️ CMO Executive Briefing - {date}</title>
    <style>
        :root {{
            --bg-primary: #0a0a0a;
            --bg-secondary: #141414;
            --bg-card: #1e1e1e;
            --text-primary: #f5f5f5;
            --text-secondary: #9ca3af;
            --accent: #8b5cf6;
            --accent-soft: rgba(139, 92, 246, 0.15);
            --critical: #ef4444;
            --critical-soft: rgba(239, 68, 68, 0.15);
            --high: #f59e0b;
            --high-soft: rgba(245, 158, 11, 0.15);
            --medium: #3b82f6;
            --medium-soft: rgba(59, 130, 246, 0.15);
            --creative: #10b981;
            --creative-soft: rgba(16, 185, 129, 0.15);
            --team: #06b6d4;
            --team-soft: rgba(6, 182, 212, 0.15);
            --border: #2a2a2a;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.7;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 850px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        header {{
            text-align: center;
            padding: 3rem 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2.5rem;
            background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
            border-radius: 16px;
        }}
        
        header h1 {{
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--accent) 0%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        header .subtitle {{
            color: var(--text-secondary);
            font-size: 1rem;
            margin-bottom: 1rem;
        }}
        
        header .meta {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            display: flex;
            justify-content: center;
            gap: 1.5rem;
            flex-wrap: wrap;
        }}
        
        header .meta span {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        
        .briefing-content {{
            background: var(--bg-secondary);
            border-radius: 16px;
            padding: 2.5rem;
            border: 1px solid var(--border);
        }}
        
        .briefing-content h1 {{
            font-size: 1.5rem;
            color: var(--accent);
            margin: 2rem 0 1rem 0;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border);
        }}
        
        .briefing-content h1:first-child {{
            margin-top: 0;
            padding-top: 0;
            border-top: none;
        }}
        
        .briefing-content h2 {{
            font-size: 1.25rem;
            color: var(--text-primary);
            margin: 1.5rem 0 0.75rem 0;
        }}
        
        .briefing-content h3 {{
            font-size: 1.1rem;
            color: var(--text-secondary);
            margin: 1.25rem 0 0.5rem 0;
        }}
        
        .briefing-content p {{
            margin-bottom: 1rem;
            color: var(--text-primary);
        }}
        
        .briefing-content ul, .briefing-content ol {{
            margin: 0.75rem 0 1rem 1.5rem;
        }}
        
        .briefing-content li {{
            margin-bottom: 0.5rem;
        }}
        
        .briefing-content strong {{
            color: var(--text-primary);
            font-weight: 600;
        }}
        
        .briefing-content em {{
            color: var(--text-secondary);
        }}
        
        .briefing-content a {{
            color: var(--accent);
            text-decoration: none;
            border-bottom: 1px dotted var(--accent);
            transition: all 0.2s;
        }}
        
        .briefing-content a:hover {{
            border-bottom-style: solid;
        }}
        
        .briefing-content hr {{
            border: none;
            border-top: 2px solid var(--border);
            margin: 2rem 0;
        }}
        
        .briefing-content blockquote {{
            border-left: 3px solid var(--accent);
            padding: 0.5rem 1rem;
            margin: 1rem 0;
            background: var(--accent-soft);
            border-radius: 0 8px 8px 0;
        }}
        
        .briefing-content code {{
            background: var(--bg-card);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-size: 0.9em;
            font-family: 'JetBrains Mono', 'Fira Code', monospace;
        }}
        
        .briefing-content pre {{
            background: var(--bg-card);
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            margin: 1rem 0;
        }}
        
        /* Priority Tags */
        .briefing-content p:has(strong:first-child) {{
            margin-top: 1.5rem;
        }}
        
        footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
            font-size: 0.8rem;
            margin-top: 2rem;
        }}
        
        footer a {{
            color: var(--accent);
            text-decoration: none;
        }}
        
        /* Print styles */
        @media print {{
            body {{
                background: white;
                color: black;
            }}
            .container {{
                max-width: 100%;
            }}
            .briefing-content {{
                background: white;
                border: 1px solid #ddd;
            }}
        }}
        
        @media (max-width: 640px) {{
            .container {{
                padding: 1rem;
            }}
            
            header h1 {{
                font-size: 1.6rem;
            }}
            
            .briefing-content {{
                padding: 1.5rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎙️ CMO Executive Briefing</h1>
            <p class="subtitle">KI-Entwicklungen für Marketing & Kommunikation</p>
            <div class="meta">
                <span>📅 {date}</span>
                <span>⏱️ {duration}</span>
                <span>📰 {source_count} Quellen</span>
            </div>
        </header>
        
        <div class="briefing-content">
            {content}
        </div>
        
        <footer>
            Generiert mit <a href="https://github.com/carstenrossi/cmo_briefing">CMO Briefing Bot</a> · Powered by Claude
        </footer>
    </div>
</body>
</html>
"""


def load_config() -> dict:
    """Lädt die Konfiguration aus config.yaml"""
    if not CONFIG_PATH.exists():
        console.print("[bold red]❌ config.yaml nicht gefunden![/]")
        console.print("   Kopiere config.example.yaml nach config.yaml und fülle deine Credentials ein.")
        sys.exit(1)
    
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def markdown_to_html(md_text: str) -> str:
    """Konvertiert Markdown zu HTML."""
    return markdown.markdown(
        md_text,
        extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists']
    )


def save_raw_news(all_news: dict, config: dict, source_count: int) -> Path:
    """Speichert alle gesammelten News als flache Markdown-Liste (ohne LLM-Verarbeitung)."""
    output_dir = Path(config.get("output", {}).get("directory", "./output"))
    output_dir.mkdir(exist_ok=True)
    
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M")
    filename = f"raw_news_{timestamp}.md"
    filepath = output_dir / filename
    
    # Header
    lines = [
        f"# 📰 Rohdaten News-Sammlung",
        f"**Datum:** {now.strftime('%d.%m.%Y %H:%M')}",
        f"**Quellen:** {source_count} ({len(all_news)} Kategorien)",
        "",
        "---",
        "",
        "*Diese Datei enthält alle gesammelten News ohne LLM-Einordnung oder Zusammenfassung.*",
        "",
        "---",
        ""
    ]
    
    # Alle News-Quellen hinzufügen
    for source_name, content in all_news.items():
        lines.append(f"# {source_name}")
        lines.append("")
        lines.append(content)
        lines.append("")
        lines.append("---")
        lines.append("")
    
    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


def save_briefing(briefing_text: str, config: dict, source_count: int) -> Path:
    """Speichert das Briefing als HTML-Datei."""
    output_dir = Path(config.get("output", {}).get("directory", "./output"))
    output_dir.mkdir(exist_ok=True)
    
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M")
    filename = f"briefing_{timestamp}.html"
    filepath = output_dir / filename
    
    # Briefing-Inhalt zu HTML konvertieren
    content_html = markdown_to_html(briefing_text)
    
    # Geschätzte Dauer berechnen (ca. 150 Wörter pro Minute)
    word_count = len(briefing_text.split())
    duration_minutes = max(5, round(word_count / 150))
    
    html_content = HTML_TEMPLATE.format(
        date=now.strftime("%d.%m.%Y"),
        duration=f"ca. {duration_minutes} Min.",
        source_count=source_count,
        content=content_html
    )
    
    filepath.write_text(html_content, encoding="utf-8")
    
    # Auch als Markdown speichern (für Copy/Paste)
    md_filepath = output_dir / f"briefing_{timestamp}.md"
    md_filepath.write_text(briefing_text, encoding="utf-8")
    
    return filepath


async def run_newsbot():
    """Hauptfunktion - sammelt News und erstellt das Executive Briefing."""
    
    console.print(Panel.fit(
        "[bold magenta]🎙️ CMO Executive Briefing Generator[/]\n"
        "Sammle KI-News für dein Podcast-Briefing...",
        border_style="magenta"
    ))
    
    # Config laden
    config = load_config()
    posts_per_source = config.get("posts_per_source", 5)
    openrouter_key = config.get("openrouter", {}).get("api_key", "")
    openrouter_model = config.get("openrouter", {}).get("model", "anthropic/claude-sonnet-4.5")
    
    if not openrouter_key or openrouter_key.startswith("sk-or-v1-xxx"):
        console.print("[bold red]❌ OpenRouter API Key fehlt in config.yaml![/]")
        sys.exit(1)
    
    sources_config = config.get("sources", {})
    
    # Hier sammeln wir ALLE formatierten News (nicht zusammengefasst!)
    all_news = {}
    total_source_count = 0  # Zählt alle einzelnen Quellen (jedes Subreddit, jede Website, etc.)
    
    # ===== REDDIT (alle Subreddits) =====
    if sources_config.get("reddit", {}).get("enabled", False):
        subreddits = sources_config["reddit"].get("subreddits", [])
        all_reddit_posts = []
        
        for subreddit in subreddits:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"[cyan]Hole r/{subreddit}...", total=None)
                
                posts = await scrape_subreddit(subreddit, max_posts=posts_per_source)
                all_reddit_posts.extend(posts)
                
                progress.update(task, description=f"[green]✓ {len(posts)} von r/{subreddit}")
        
        if all_reddit_posts:
            formatted = format_reddit(all_reddit_posts)
            all_news["Reddit"] = formatted
            total_source_count += len(subreddits)  # Jedes Subreddit zählt als Quelle
            console.print(f"  [dim]→ {len(all_reddit_posts)} Reddit-Posts aus {len(subreddits)} Subreddits[/]")
    
    # ===== LINKEDIN =====
    if sources_config.get("linkedin", {}).get("enabled", False):
        linkedin_config = sources_config["linkedin"]
        email = linkedin_config.get("email", "")
        password = linkedin_config.get("password", "")
        linkedin_posts_count = linkedin_config.get("posts_count", posts_per_source)
        
        if email and password:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Hole LinkedIn Feed...", total=None)
                
                posts = await scrape_linkedin_feed(email, password, max_posts=linkedin_posts_count)
                
                progress.update(task, description=f"[green]✓ {len(posts)} LinkedIn-Posts")
            
            if posts:
                formatted = format_linkedin(posts)
                all_news["LinkedIn"] = formatted
                total_source_count += 1
    
    # ===== FUTURISM =====
    if sources_config.get("futurism", {}).get("enabled", False):
        futurism_count = sources_config["futurism"].get("posts_count", 5)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Hole Futurism AI News...", total=None)
            
            articles = await scrape_futurism(max_articles=futurism_count)
            
            progress.update(task, description=f"[green]✓ {len(articles)} Futurism-Artikel")
        
        if articles:
            formatted = format_futurism(articles)
            all_news["Futurism"] = formatted
            total_source_count += 1
    
    # ===== THE NEURON =====
    if sources_config.get("theneuron", {}).get("enabled", False):
        neuron_count = sources_config["theneuron"].get("posts_count", 5)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Hole The Neuron Newsletter...", total=None)
            
            articles = await scrape_theneuron(max_articles=neuron_count)
            
            progress.update(task, description=f"[green]✓ {len(articles)} Neuron-Artikel")
        
        if articles:
            formatted = format_neuron(articles)
            all_news["The Neuron"] = formatted
            total_source_count += 1
    
    # ===== WEB NEWS SOURCES =====
    if sources_config.get("web_sources", {}).get("enabled", False):
        web_config = sources_config["web_sources"]
        web_posts_count = web_config.get("posts_count", 5)
        source_keys = web_config.get("sources", [])
        
        all_web_articles = []
        
        for source_key in source_keys:
            if source_key not in SITE_CONFIGS:
                continue
            source_name = SITE_CONFIGS[source_key]["name"]
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"[cyan]Hole {source_name}...", total=None)
                
                articles = await scrape_web_source(source_key, max_articles=web_posts_count)
                all_web_articles.extend(articles)
                
                progress.update(task, description=f"[green]✓ {len(articles)} von {source_name}")
        
        if all_web_articles:
            formatted = format_articles_for_llm(all_web_articles, "Web News")
            all_news["Web News"] = formatted
            total_source_count += len(source_keys)  # Jede Website zählt als Quelle
            console.print(f"  [dim]→ {len(all_web_articles)} Web-Artikel aus {len(source_keys)} Seiten[/]")
    
    # ===== EXECUTIVE BRIEFING ERSTELLEN =====
    if not all_news:
        console.print("[yellow]Keine News gefunden oder alle Quellen deaktiviert.[/]")
        return
    
    console.print("\n")
    console.print(Panel.fit(
        f"[bold cyan]📊 News-Sammlung abgeschlossen[/]\n\n"
        f"Quellen: {total_source_count} ({len(all_news)} Kategorien)\n"
        f"Sende an Claude für Executive Briefing...",
        border_style="cyan"
    ))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(
            "[magenta]🎙️ Erstelle Executive Briefing (kann 1-2 Minuten dauern)...", 
            total=None
        )
        
        briefing = await create_executive_briefing(
            all_news,
            openrouter_key,
            openrouter_model
        )
        
        progress.update(task, description="[green]✓ Executive Briefing erstellt!")
    
    # Prüfen ob Fehler
    if briefing.startswith("❌"):
        console.print(f"\n[bold red]{briefing}[/]")
        return
    
    # Rohdaten speichern (flache Liste ohne LLM-Verarbeitung)
    raw_filepath = save_raw_news(all_news, config, total_source_count)
    
    # Briefing speichern
    filepath = save_briefing(briefing, config, total_source_count)
    
    console.print("\n")
    console.print(Panel.fit(
        f"[bold green]✅ Executive Briefing fertig![/]\n\n"
        f"📄 Briefing HTML: [cyan]{filepath}[/]\n"
        f"📝 Briefing MD:   [cyan]{filepath.with_suffix('.md')}[/]\n"
        f"📰 Rohdaten:      [cyan]{raw_filepath}[/]\n\n"
        f"Das Briefing wurde aus {total_source_count} Quellen erstellt.",
        border_style="green"
    ))
    
    # Report im Browser öffnen
    try:
        webbrowser.open(f"file://{filepath.absolute()}")
    except:
        pass


def main():
    """Entry point."""
    if "--help" in sys.argv or "-h" in sys.argv:
        console.print(__doc__)
        return
    
    try:
        asyncio.run(run_newsbot())
    except KeyboardInterrupt:
        console.print("\n[yellow]Abgebrochen.[/]")
    except Exception as e:
        console.print(f"[bold red]Fehler: {e}[/]")
        raise


if __name__ == "__main__":
    main()
