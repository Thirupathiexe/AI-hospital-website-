"""Deterministic red-flag check. Runs BEFORE any AI call, so urgent cases never depend on a model."""
from __future__ import annotations

import re

_RED_FLAGS = [
    r"sudden(ly)?\b.{0,40}\b(loss|lost|lose|blur\w*|blind|see|dark|black|vision|sight)",
    r"\b(vision|sight|eyesight|see|eye)\b.{0,40}\bsudden(ly)?\b",
    r"(lost|losing|loss of)\s+(my\s+)?(vision|sight|eyesight)",
    r"\b(vision|sight|eyesight)\b.{0,15}\b(went|gone|going|turned)\s+(dark|black|blank|white)",
    r"\b(went|gone|going)\s+blind\b|\bcan'?t see (anything|at all)\b",
    r"\bchemical\b|\bacid\b|\bbleach\b",
    r"\b(injur|hit|struck|punched|stabbed|cut)\w*\b.*\beye\b|\beye\b.*\b(injur|hit|struck|cut)\w*",
    r"\bcurtain\b|\bshadow over\b",
    r"\bflash(es|ing)?\b.*\bfloat|\bfloat\w*\b.*\bflash",
    r"severe\s+(eye\s+)?pain|unbearable\s+pain",
    r"\bblood\b.*\beye\b|\beye\b.*\bbleed",
]
_PATTERN = re.compile("|".join(_RED_FLAGS), re.IGNORECASE)

URGENT_REPLY = ("This sounds urgent. Please go to the nearest emergency department or call emergency services right now. "
                "If a chemical got in your eye, rinse it with clean water for at least 15 minutes on the way. "
                "Please don't wait for a clinic appointment.")


def red_flag_reply(text: str) -> str | None:
    return URGENT_REPLY if _PATTERN.search(text or "") else None
