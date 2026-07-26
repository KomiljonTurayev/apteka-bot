import os
from dotenv import load_dotenv

load_dotenv()

# Strip any leading/trailing whitespace, newlines or accidental quotes from Railway env vars
raw_bot_token = os.getenv("BOT_TOKEN", "")
BOT_TOKEN = raw_bot_token.strip().strip('"').strip("'") if raw_bot_token else ""

raw_anthropic = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_KEY = raw_anthropic.strip().strip('"').strip("'") if raw_anthropic else ""

# Parse admin IDs from env string
admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(i.strip()) for i in admin_ids_raw.split(",") if i.strip().isdigit()]

# GitHub Credentials
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL", "").strip()

# PostgreSQL & SQLite Database Connection
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_PATH = "pharmacy.db"
