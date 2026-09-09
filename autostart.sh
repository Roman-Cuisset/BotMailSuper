#!/bin/bash

# --- 1. Lancement du BOT ---
SESSION_BOT="bot_session"
tmux has-session -t $SESSION_BOT 2>/dev/null
if [ $? != 0 ]; then
  tmux new-session -d -s $SESSION_BOT
  # On lance le bot
  tmux send-keys -t $SESSION_BOT "cd ~/workspace/telegram_mail_bot && source .venv/bin/activate && python3 main_pro.py" C-m
fi

# --- 2. Lancement de l'INTERFACE WEB ---
SESSION_WEB="web_session"
tmux has-session -t $SESSION_WEB 2>/dev/null
if [ $? != 0 ]; then
  tmux new-session -d -s $SESSION_WEB
  # On lance le serveur web
  tmux send-keys -t $SESSION_WEB "cd ~/workspace/telegram_mail_bot && source .venv/bin/activate && python3 web_admin.py" C-m
fi
