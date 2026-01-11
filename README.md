# 📰 Personal Newsbot

Ein persönlicher News-Aggregator, der Posts von LinkedIn und Reddit holt und mit KI zusammenfasst.

## Features

- 🔐 **LinkedIn Feed** - Holt deine Timeline-Posts (mit Login)
- 🤖 **Reddit** - Scraped öffentliche Subreddits (z.B. r/ClaudeAI)
- 🧠 **LLM-Zusammenfassung** - Nutzt OpenRouter/Claude für intelligente Summaries
- 📄 **Markdown-Reports** - Sauber formatierte, datierte Ausgabe

## Setup

### 1. Python-Umgebung

```bash
# Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Playwright Browser installieren
playwright install chromium
```

### 2. Konfiguration

```bash
# Config-Datei erstellen
cp config.example.yaml config.yaml
```

Dann `config.yaml` bearbeiten und eintragen:
- OpenRouter API Key (https://openrouter.ai/keys)
- LinkedIn Credentials
- Gewünschte Subreddits

### 3. Ausführen

```bash
python main.py
```

Der Report wird im `output/` Ordner gespeichert.

## Konfiguration

```yaml
# config.yaml
openrouter:
  api_key: "sk-or-v1-..."
  model: "anthropic/claude-3.5-sonnet"

posts_per_source: 20

sources:
  reddit:
    enabled: true
    subreddits:
      - "ClaudeAI"
      - "LocalLLaMA"

  linkedin:
    enabled: true
    email: "deine@email.com"
    password: "dein-passwort"
```

## Hinweise

### LinkedIn
- Beim ersten Login wird ein Browser-Fenster geöffnet (nicht headless)
- Falls LinkedIn einen Security-Check verlangt, manuell bestätigen
- Cookies werden in `.linkedin_cookies.json` gespeichert für spätere Sessions

### Rate Limits
- Nicht zu häufig ausführen (1x täglich empfohlen)
- LinkedIn kann Accounts temporär sperren bei zu viel Automation

### Kosten
- OpenRouter berechnet nach Tokens
- Ein Durchlauf mit 20 Posts pro Quelle: ca. $0.01-0.05

## Struktur

```
news/
├── main.py                 # Hauptscript
├── config.yaml             # Deine Credentials (gitignored!)
├── config.example.yaml     # Template
├── requirements.txt
├── sources/
│   ├── reddit.py          # Reddit Scraper
│   └── linkedin.py        # LinkedIn Scraper
├── llm/
│   └── summarizer.py      # OpenRouter Integration
└── output/
    └── news_2025-01-07_15-30.md
```

## Erweiterung

Neue Quellen hinzufügen:
1. Neuen Scraper in `sources/` erstellen
2. `format_posts_for_llm()` Funktion implementieren
3. In `main.py` einbinden

---

Made with ☕ and Claude


