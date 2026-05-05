# ── Config ────────────────────────────────────────────────────────────────────
import os

import openai

TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
MINI_APP_URL   = os.environ["MINI_APP_URL"]   # e.g. https://yourdomain.com/miniapp/

openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)