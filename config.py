# config.py

import os
from dotenv import load_dotenv

# Load variables from .env located at project root
load_dotenv()

# — Paths & credentials used by nea_reports.py —
BASE_NEA = os.environ.get("BASE_NEA", r"Q:\\03. MONTHLY REPORT_EXTERNAL COPY\\NEA\\NEA Portal")
BASE_ERC = os.environ.get("BASE_ERC", r"Q:\\03. MONTHLY REPORT_EXTERNAL COPY\\ERC\\OUTAGES")

SENDER_EMAIL     = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD  = os.environ.get("SENDER_PASSWORD")
RECIPIENT_EMAILS = os.environ.get("RECIPIENT_EMAILS", "").split(',') if os.environ.get("RECIPIENT_EMAILS") else []

TESSERACT_CMD = os.environ.get("TESSERACT_CMD", r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe")

# — Flask / SQLAlchemy config —
basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = os.environ.get(
    "DATABASE_URL",
    "sqlite:///" + os.path.join(basedir, "dashboard.sqlite")
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# — APScheduler timezone —
SCHEDULER_TIMEZONE = os.environ.get("SCHEDULER_TIMEZONE", "Asia/Manila")
