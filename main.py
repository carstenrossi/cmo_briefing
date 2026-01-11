#!/usr/bin/env python3
"""
📰 Personal Newsbot
Holt und fasst News von LinkedIn und Reddit zusammen.

Usage:
    python main.py          # Führt den Newsbot aus
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
from llm.summarizer import summarize_posts, create_combined_summary


console = Console()

# Konfiguration laden
CONFIG_PATH = Path(__file__).parent / "config.yaml"
OUTPUT_DIR = Path(__file__).parent / "output"


# HTML Template mit modernem Design
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📰 News Report - {date}</title>
    <style>
        :root {{
            --bg-primary: #0f0f0f;
            --bg-secondary: #1a1a1a;
            --bg-card: #242424;
            --text-primary: #e8e8e8;
            --text-secondary: #a0a0a0;
            --accent: #6366f1;
            --accent-hover: #818cf8;
            --border: #333;
            --success: #22c55e;
            --reddit: #ff4500;
            --linkedin: #0a66c2;
            --futurism: #00d4aa;
            --webnews: #f59e0b;
            --neuron: #ec4899;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: 'SF Pro Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        header {{
            text-align: center;
            padding: 3rem 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 2rem;
        }}
        
        header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--accent) 0%, #a855f7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        header .meta {{
            color: var(--text-secondary);
            font-size: 0.95rem;
        }}
        
        .source-section {{
            background: var(--bg-secondary);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 2rem;
            border: 1px solid var(--border);
        }}
        
        .source-section h2 {{
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .source-section.reddit h2 {{
            color: var(--reddit);
        }}
        
        .source-section.linkedin h2 {{
            color: var(--linkedin);
        }}
        
        .source-section.futurism h2 {{
            color: var(--futurism);
        }}
        
        .source-section.webnews h2 {{
            color: var(--webnews);
        }}
        
        .source-section.neuron h2 {{
            color: var(--neuron);
        }}
        
        .source-section.meta-summary h2 {{
            color: var(--accent);
        }}
        
        .badge {{
            font-size: 0.75rem;
            padding: 0.25rem 0.75rem;
            border-radius: 999px;
            font-weight: 500;
        }}
        
        .badge.reddit {{
            background: rgba(255, 69, 0, 0.15);
            color: var(--reddit);
        }}
        
        .badge.linkedin {{
            background: rgba(10, 102, 194, 0.15);
            color: var(--linkedin);
        }}
        
        .badge.futurism {{
            background: rgba(0, 212, 170, 0.15);
            color: var(--futurism);
        }}
        
        .badge.webnews {{
            background: rgba(245, 158, 11, 0.15);
            color: var(--webnews);
        }}
        
        .badge.neuron {{
            background: rgba(236, 72, 153, 0.15);
            color: var(--neuron);
        }}
        
        .content {{
            color: var(--text-primary);
        }}
        
        .content h1, .content h2, .content h3 {{
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            color: var(--text-primary);
        }}
        
        .content h1 {{ font-size: 1.4rem; }}
        .content h2 {{ font-size: 1.2rem; }}
        .content h3 {{ font-size: 1.1rem; color: var(--text-secondary); }}
        
        .content p {{
            margin-bottom: 1rem;
        }}
        
        .content ul, .content ol {{
            margin: 1rem 0;
            padding-left: 1.5rem;
        }}
        
        .content li {{
            margin-bottom: 0.5rem;
        }}
        
        .content a {{
            color: var(--accent);
            text-decoration: none;
            transition: color 0.2s;
        }}
        
        .content a:hover {{
            color: var(--accent-hover);
            text-decoration: underline;
        }}
        
        .content strong {{
            color: var(--text-primary);
            font-weight: 600;
        }}
        
        .content em {{
            color: var(--text-secondary);
        }}
        
        .content blockquote {{
            border-left: 3px solid var(--accent);
            padding-left: 1rem;
            margin: 1rem 0;
            color: var(--text-secondary);
            font-style: italic;
        }}
        
        .content code {{
            background: var(--bg-card);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        
        .content hr {{
            border: none;
            border-top: 1px solid var(--border);
            margin: 1.5rem 0;
        }}
        
        footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
            font-size: 0.85rem;
            border-top: 1px solid var(--border);
            margin-top: 2rem;
        }}
        
        footer a {{
            color: var(--accent);
            text-decoration: none;
        }}
        
        @media (max-width: 640px) {{
            .container {{
                padding: 1rem;
            }}
            
            header h1 {{
                font-size: 1.8rem;
            }}
            
            .source-section {{
                padding: 1.25rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📰 News Report</h1>
            <p class="meta">Erstellt am {date} um {time} Uhr · {post_count} Posts pro Quelle</p>
        </header>
        
        <main>
            {sections}
        </main>
        
        <footer>
            Generiert mit <a href="#">Personal Newsbot</a> · Powered by OpenRouter
        </footer>
    </div>
</body>
</html>
"""

SECTION_TEMPLATE = """
<section class="source-section {source_class}">
    <h2>
        {icon} {title}
        <span class="badge {source_class}">{badge_text}</span>
    </h2>
    <div class="content">
        {content}
    </div>
</section>
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
        extensions=['tables', 'fenced_code', 'nl2br']
    )


def save_report(sections_html: str, config: dict, post_count: int) -> Path:
    """Speichert den Report als HTML-Datei."""
    output_dir = Path(config.get("output", {}).get("directory", "./output"))
    output_dir.mkdir(exist_ok=True)
    
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d_%H-%M")
    filename = f"news_{timestamp}.html"
    filepath = output_dir / filename
    
    html_content = HTML_TEMPLATE.format(
        date=now.strftime("%d.%m.%Y"),
        time=now.strftime("%H:%M"),
        post_count=post_count,
        sections=sections_html
    )
    
    filepath.write_text(html_content, encoding="utf-8")
    return filepath


def create_section_html(source: str, summary: str) -> str:
    """Erstellt HTML für eine Quellen-Sektion."""
    # Source-spezifische Einstellungen
    if "reddit" in source.lower():
        source_class = "reddit"
        icon = "🔴"
        badge_text = "Reddit"
    elif "linkedin" in source.lower():
        source_class = "linkedin"
        icon = "💼"
        badge_text = "LinkedIn"
    elif "futurism" in source.lower():
        source_class = "futurism"
        icon = "🚀"
        badge_text = "Futurism"
    elif "neuron" in source.lower():
        source_class = "neuron"
        icon = "🧠"
        badge_text = "The Neuron"
    elif "web news" in source.lower():
        source_class = "webnews"
        icon = "🌐"
        badge_text = "Web News"
    else:
        source_class = "meta-summary"
        icon = "🔗"
        badge_text = "Überblick"
    
    # Markdown zu HTML konvertieren
    content_html = markdown_to_html(summary)
    
    return SECTION_TEMPLATE.format(
        source_class=source_class,
        icon=icon,
        title=source,
        badge_text=badge_text,
        content=content_html
    )


async def run_newsbot():
    """Hauptfunktion - führt den kompletten Newsbot-Workflow aus."""
    
    console.print(Panel.fit(
        "[bold cyan]📰 Personal Newsbot[/]\n"
        "Hole und fasse deine News zusammen...",
        border_style="cyan"
    ))
    
    # Config laden
    config = load_config()
    posts_per_source = config.get("posts_per_source", 20)
    openrouter_key = config.get("openrouter", {}).get("api_key", "")
    openrouter_model = config.get("openrouter", {}).get("model", "anthropic/claude-3.5-sonnet")
    
    if not openrouter_key or openrouter_key.startswith("sk-or-v1-xxx"):
        console.print("[bold red]❌ OpenRouter API Key fehlt in config.yaml![/]")
        sys.exit(1)
    
    sources_config = config.get("sources", {})
    all_posts = {}
    summaries = {}
    
    # ===== REDDIT (alle Subreddits gebündelt) =====
    if sources_config.get("reddit", {}).get("enabled", False):
        subreddits = sources_config["reddit"].get("subreddits", [])
        all_reddit_posts = []
        
        for subreddit in subreddits:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"[cyan]Hole r/{subreddit} Posts...", total=None)
                
                posts = await scrape_subreddit(subreddit, max_posts=posts_per_source)
                all_reddit_posts.extend(posts)
                
                progress.update(task, description=f"[green]✓ {len(posts)} Posts von r/{subreddit}")
        
        # Eine gebündelte Zusammenfassung für alle Reddit-Posts
        if all_reddit_posts:
            console.print(f"\n  [dim]→ Erstelle gebündelte Reddit-Zusammenfassung ({len(all_reddit_posts)} Posts)...[/]")
            formatted = format_reddit(all_reddit_posts)
            subreddit_list = ", ".join([f"r/{s}" for s in subreddits])
            summary = await summarize_posts(
                formatted, 
                f"Reddit ({subreddit_list})",
                openrouter_key,
                openrouter_model
            )
            summaries["Reddit Übersicht"] = summary
            console.print(f"  [green]✓ Reddit-Zusammenfassung fertig[/]")
    
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
                all_posts["LinkedIn"] = posts
                
                progress.update(task, description=f"[green]✓ {len(posts)} Posts von LinkedIn")
            
            if posts:
                console.print(f"  [dim]→ Zusammenfassung wird erstellt...[/]")
                formatted = format_linkedin(posts)
                summary = await summarize_posts(
                    formatted,
                    "LinkedIn",
                    openrouter_key,
                    openrouter_model
                )
                summaries["LinkedIn Feed"] = summary
                console.print(f"  [green]✓ Zusammenfassung fertig[/]")
        else:
            console.print("[yellow]⚠️  LinkedIn Credentials fehlen in config.yaml[/]")
    
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
            
            progress.update(task, description=f"[green]✓ {len(articles)} Artikel von Futurism")
        
        if articles:
            console.print(f"  [dim]→ Zusammenfassung wird erstellt...[/]")
            formatted = format_futurism(articles)
            summary = await summarize_posts(
                formatted,
                "Futurism.com",
                openrouter_key,
                openrouter_model
            )
            summaries["Futurism AI News"] = summary
            console.print(f"  [green]✓ Zusammenfassung fertig[/]")
    
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
            
            progress.update(task, description=f"[green]✓ {len(articles)} Artikel von The Neuron")
        
        if articles:
            console.print(f"  [dim]→ Zusammenfassung wird erstellt...[/]")
            formatted = format_neuron(articles)
            summary = await summarize_posts(
                formatted,
                "The Neuron",
                openrouter_key,
                openrouter_model
            )
            summaries["The Neuron Newsletter"] = summary
            console.print(f"  [green]✓ Zusammenfassung fertig[/]")
    
    # ===== WEB NEWS SOURCES (gebündelt) =====
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
                
                progress.update(task, description=f"[green]✓ {len(articles)} Artikel von {source_name}")
        
        # Eine gebündelte Zusammenfassung für alle Web-Quellen
        if all_web_articles:
            console.print(f"\n  [dim]→ Erstelle gebündelte Web-News-Zusammenfassung ({len(all_web_articles)} Artikel)...[/]")
            formatted = format_articles_for_llm(all_web_articles, "Web News")
            source_list = ", ".join([SITE_CONFIGS[k]["name"] for k in source_keys if k in SITE_CONFIGS])
            summary = await summarize_posts(
                formatted,
                f"Web News ({source_list})",
                openrouter_key,
                openrouter_model
            )
            summaries["Web News Übersicht"] = summary
            console.print(f"  [green]✓ Web-News-Zusammenfassung fertig[/]")
    
    # ===== REPORT ERSTELLEN =====
    if not summaries:
        console.print("[yellow]Keine Posts gefunden oder alle Quellen deaktiviert.[/]")
        return
    
    console.print("\n[cyan]Erstelle HTML Report...[/]")
    
    # Sektionen als HTML erstellen
    sections_html = ""
    for source, summary in summaries.items():
        sections_html += create_section_html(source, summary)
    
    # Optionale Meta-Zusammenfassung
    if len(summaries) > 1:
        console.print("  [dim]→ Erstelle übergreifende Zusammenfassung...[/]")
        meta_summary = await create_combined_summary(summaries, openrouter_key, openrouter_model)
        if meta_summary:
            sections_html += create_section_html("Übergreifende Themen", meta_summary)
    
    # Speichern
    filepath = save_report(sections_html, config, posts_per_source)
    
    console.print(Panel.fit(
        f"[bold green]✅ Report erstellt![/]\n\n"
        f"📄 [cyan]{filepath}[/]\n\n"
        f"Quellen: {', '.join(summaries.keys())}",
        border_style="green"
    ))
    
    # Optional: Report im Browser öffnen
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
