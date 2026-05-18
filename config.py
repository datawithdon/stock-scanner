import os

EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
EMAIL_TO = os.environ.get("EMAIL_TO", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# Technical scanner
VOLUME_SURGE_MIN = 3.0
BREAKOUT_LOOKBACK = 20
RSI_PERIOD = 14
RSI_MIN = 50
RSI_MAX = 75
MIN_PRICE = 2.0
MAX_PRICE = 50.0
MIN_AVG_VOLUME = 100_000
TOP_N = 20
FETCH_WORKERS = 10

# News scanner
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
NEWS_LOOKBACK_HOURS = 20          # How far back to scan RSS / EDGAR
REDDIT_LOOKBACK_HOURS = 24
NEWS_MIN_SCORE = 5                # Claude score threshold (0–10) to include in email
NEWS_TOP_N = 25                   # Max stocks in news alert email
