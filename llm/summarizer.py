"""
OpenRouter LLM Integration für Post-Zusammenfassungen
Optimiert für KI-Berater in Agenturen
"""

import httpx
from typing import Optional


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """Du bist ein strategischer Analyst für einen KI-Berater, der in einer Agentur arbeitet. 
Deine Aufgabe ist es, KI-News und Diskussionen so aufzubereiten, dass der Berater sofort erkennt:

1. **Kundenrelevanz**: Was davon ist für Kunden interessant? Welche Branchen/Use Cases profitieren?
2. **Service-Potenzial**: Welche neuen Services oder Angebote könnte die Agentur daraus entwickeln?
3. **Wettbewerbsvorteil**: Was sollte man wissen, um Kunden kompetent zu beraten?
4. **Handlungsbedarf**: Gibt es dringende Entwicklungen, auf die man reagieren sollte?

Dein Stil:
- Schreibe auf Deutsch
- Sei prägnant und actionable
- Priorisiere nach Business-Relevanz
- Markiere besonders wichtige Insights mit 🔥
- WICHTIG: Verlinke JEDEN erwähnten Post mit seiner Original-URL (im Format [Beschreibung](URL))
- Nutze die POST-URLs aus den Quelldaten - sie sind klickbare Links zum Originalpost

Format:
- Nutze Markdown
- Gliedere nach Relevanz-Kategorien (nicht nach Quelle)
- Füge konkrete Handlungsempfehlungen hinzu
"""

USER_PROMPT_TEMPLATE = """Hier sind die neuesten Posts von {source}:

{posts}

---

Analysiere diese Posts aus der Perspektive eines KI-Beraters einer Agentur:

1. **🔥 Top-Insights für die Kundenberatung** - Was muss man diese Woche wissen?
2. **💡 Service-Ideen** - Welche neuen Angebote könnte man daraus entwickeln?
3. **📊 Markt & Trends** - Wohin entwickelt sich die KI-Landschaft?
4. **⚠️ Watchlist** - Was sollte man im Auge behalten?

Fokussiere auf Actionable Insights, nicht auf allgemeine Zusammenfassungen.
"""


async def summarize_posts(
    posts_text: str,
    source_name: str,
    api_key: str,
    model: str = "anthropic/claude-sonnet-4.5"
) -> str:
    """
    Nutzt OpenRouter um Posts zusammenzufassen.
    """
    if not posts_text or posts_text.strip() == "":
        return f"Keine Posts von {source_name} zum Zusammenfassen."
    
    user_prompt = USER_PROMPT_TEMPLATE.format(
        source=source_name,
        posts=posts_text
    )
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/newsbot",
        "X-Title": "Personal Newsbot"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 2500,
        "temperature": 0.3
    }
    
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
    except httpx.HTTPStatusError as e:
        return f"❌ API-Fehler: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"❌ Fehler bei der Zusammenfassung: {str(e)}"


async def create_combined_summary(
    summaries: dict[str, str],
    api_key: str,
    model: str = "anthropic/claude-sonnet-4.5"
) -> Optional[str]:
    """
    Erstellt eine strategische Zusammenfassung aller Quellen.
    """
    if len(summaries) < 2:
        return None
    
    combined_text = "\n\n---\n\n".join([
        f"## {source}\n{summary}" 
        for source, summary in summaries.items()
    ])
    
    user_prompt = f"""Hier sind die Analysen von verschiedenen Quellen:

{combined_text}

---

Erstelle eine **Executive Summary** für den KI-Berater:

1. **🎯 Die 3 wichtigsten Erkenntnisse heute** - Was muss ich meinen Kunden erzählen?
2. **🚀 Quick Wins** - Was kann ich sofort in Kundengesprächen nutzen?
3. **📅 Diese Woche im Blick** - Welche Themen sollte ich vertiefen?

Halte es kurz und auf den Punkt. Maximal 300 Wörter."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Du bist ein strategischer Berater, der komplexe Informationen auf das Wesentliche reduziert. Fokus auf Actionable Insights."},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 1000,
        "temperature": 0.3
    }
    
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except:
        return None
