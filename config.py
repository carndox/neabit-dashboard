# config.py

import os

# — Paths & credentials used by nea_reports.py —
BASE_NEA = r"Q:\03. MONTHLY REPORT_EXTERNAL COPY\NEA\NEA Portal"
BASE_ERC = r"Q:\03. MONTHLY REPORT_EXTERNAL COPY\ERC\OUTAGES"

SENDER_EMAIL     = "c3enggagent@gmail.com"
SENDER_PASSWORD  = "zkcd dbel udfu fzhr"
RECIPIENT_EMAILS = [
    "edgardoghernaezthe3rd@gmail.com",
    "radihernaez@gmail.com",
    "tangarosandra@gmail.com"
]

TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# — Flask / SQLAlchemy config —
basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "dashboard.sqlite")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# — APScheduler timezone —
SCHEDULER_TIMEZONE = "Asia/Manila"
