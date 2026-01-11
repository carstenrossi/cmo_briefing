#!/bin/zsh
# Newsbot Starter - Doppelklick zum Ausführen

cd "$(dirname "$0")"
source venv/bin/activate
python main.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Newsbot fertig! Drücke Enter zum Schließen."
read


