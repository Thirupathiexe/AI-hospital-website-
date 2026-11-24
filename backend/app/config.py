"""All settings come from environment variables (or backend/.env). Nothing secret is hard-coded."""
from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

# Clinic runs on India time. A fixed offset avoids needing tz data on Windows.
CLINIC_TZ = timezone(timedelta(hours=5, minutes=30))

DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'netracare.db'}")

# Signing key for login tokens. If unset, a random one is made at start-up
# (everyone is logged out when the server restarts, which is safe).
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(48)
TOKEN_TTL_MINUTES = int(os.getenv("TOKEN_TTL_MINUTES", "480"))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

# Optional shared codes. Empty = the brief's "no password" login.
STAFF_ACCESS_CODE = os.getenv("STAFF_ACCESS_CODE", "")
DOCTOR_ACCESS_CODE = os.getenv("DOCTOR_ACCESS_CODE", "")

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

# AI assistant
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")
AI_ENABLED = os.getenv("AI_ENABLED", "true").lower() == "true"

# Fixed clock for tests/demos, e.g. CLINIC_NOW=2026-11-02 10:00
CLINIC_NOW = os.getenv("CLINIC_NOW", "")

BOOKING_WINDOW_DAYS = 30
PATIENT_CANCEL_CUTOFF_HOURS = 2


def now() -> datetime:
    """Clinic wall-clock time (naive, India time). Every rule uses this one function."""
    fixed = os.getenv("CLINIC_NOW", CLINIC_NOW)
    if fixed:
        return datetime.strptime(fixed, "%Y-%m-%d %H:%M")
    return datetime.now(CLINIC_TZ).replace(tzinfo=None, second=0, microsecond=0)
