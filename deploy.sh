#!/bin/bash
echo "🚀 Deploying Apteka AI Bot to Server..."

# Pull latest code from GitHub
git pull origin main

# Setup Virtual Environment if not exists
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

# Activate & Install requirements
source .venv/bin/activate
pip install -r requirements.txt

# Build database if needed
python seed_db.py

# Restart systemd service if configured
if systemctl is-active --quiet apteka-bot; then
    sudo systemctl restart apteka-bot
    echo "✅ Service restarted successfully!"
else
    echo "ℹ️ Systemd service 'apteka-bot' not enabled. Run manually with: python main.py"
fi
