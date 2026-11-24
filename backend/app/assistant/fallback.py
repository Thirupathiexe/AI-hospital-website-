"""Basic assistant used when no Anthropic API key is set (or the AI is unreachable).
Understands simple requests like:
  "show doctors" / "who treats glaucoma"
  "my appointments"
  "free slots with Dr Rao tomorrow"
  "book Dr Shah on Friday at 10:30 for retina"   -> asks to confirm, then "yes"
  "cancel A012"                                  -> asks to confirm, then "yes"
It uses the same rule-checked functions as the website."""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from sqlmodel import Session, select

from .. import config, rules, services
from ..models import Doctor
from ..rules import Actor, RuleError

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
SPEC_WORDS = {"cataract": "Cataract", "glaucoma": "Glaucoma", "retina": "Retina", "cornea": "Cornea",
              "refractive": "Refractive", "lasik": "Refractive", "glasses": "Refractive", "dry eye": "Dry eye",
              "dry eyes": "Dry eye", "paediatric": "Paediatric", "pediatric": "Paediatric", "child": "Paediatric",
              "kid": "Paediatric", "squint": "Squint", "general": "General", "checkup": "General", "check-up": "General"}
YES = re.compile(r"^\s*(yes|yeah|yep|sure|ok(ay)?|confirm|go ahead|please do|do it|haan|ha)\b", re.I)
NO = re.compile(r"^\s*(no|nope|cancel that|don'?t|stop)\b", re.I)


def _t12(hhmm: str) -> str:
    return rules.fmt12(rules.parse_time(hhmm))


def _d(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%A %d %B")


def parse_date(text: str, today: date) -> Optional[date]:
    t = text.lower()
    if "day after tomorrow" in t:
        return today + timedelta(days=2)
    if "tomorrow" in t:
        return today + timedelta(days=1)
    if "today" in t:
        return today
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3]))
        except ValueError:
            return None
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(" + "|".join(MONTHS) + r")[a-z]*", t) or \
        re.search(r"\b(" + "|".join(MONTHS) + r")[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\b", t)
    if m:
        a, b = m[1], m[2]
        day, mon = (int(a), b) if a.isdigit() else (int(b), a)
        month = MONTHS.index(mon[:3]) + 1
        try:
            d = date(today.year, month, day)
            return d if d >= today else date(today.year + 1, month, day)
        except ValueError:
            return None
    m = re.search(r"\b(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?\b", t)
    if m and not re.search(r"\d{1,2}[.:]\d{2}\s*(am|pm)", t):
        try:
            year = int(m[3]) + (2000 if m[3] and len(m[3]) == 2 else 0) if m[3] else today.year
            return date(year, int(m[2]), int(m[1]))
        except ValueError:
            return None
    for i, w in enumerate(WEEKDAYS):
        if re.search(rf"\b{w}\b", t):
            delta = (i - today.weekday()) % 7
            if "next" in t and delta == 0:
                delta = 7
            return today + timedelta(days=delta)
    return None


def parse_time(text: str) -> Optional[str]:
    t = text.lower().replace("a.m.", "am").replace("p.m.", "pm")
    m = re.search(r"\b(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)\b", t) or re.search(r"\bat\s+(\d{1,2})(?:[:.](\d{2}))?\b", t) \
        or re.search(r"\b(\d{1,2})[:.](\d{2})\b", t)
    if not m:
        return None
    h, mi = int(m[1]), int(m[2] or 0)
    ampm = m[3] if m.lastindex and m.lastindex >= 3 else None
    if ampm == "pm" and h < 12:
        h += 12
    if ampm == "am" and h == 12:
        h = 0
    if not ampm and 1 <= h <= 6:  # "at 3" in a clinic means 3 PM
        h += 12
    if h > 23 or mi > 59:
        return None
    return f"{h:02d}:{mi:02d}"


def find_doctor(s: Session, text: str) -> Optional[Doctor]:
    t = text.lower()
    for d in s.exec(select(Doctor)).all():
        parts = [p.lower().strip(".") for p in d.name.split() if p.lower().strip(".") != "dr"]
        if any(re.search(rf"\b{re.escape(p)}\b", t) for p in parts) or d.id.lower() in t.split():
            return d
    return None


def find_speciality(text: str) -> Optional[str]:
    t = text.lower()
    for word, spec in SPEC_WORDS.items():
        if word in t:
            return spec
    return None


def handle(s: Session, actor: Actor, message: str, conv: dict) -> tuple[str, list]:
    text = message.strip()
    low = text.lower()
    today = config.now().date()
    pending = conv.get("pending")

    if pending and YES.search(low):
        conv["pending"] = None
        try:
            if pending["action"] == "book":
                appt = rules.book(s, actor, **pending["args"])
                out = services.appointment_out(s, appt, actor)
                return (f"Done. You're booked with {out['doctor_name']} on {_d(out['date'])} at {_t12(out['start_time'])}. "
                        f"Your appointment number is {out['id']}."), [{"type": "booked", "appointment": out}]
            appt = rules.cancel(s, actor, pending["args"]["appointment_id"])
            out = services.appointment_out(s, appt, actor)
            return f"Appointment {out['id']} is cancelled.", [{"type": "cancelled", "appointment": out}]
        except RuleError as e:
            s.rollback()
            return f"Sorry, I couldn't do that. {e.message}", []
    if pending and NO.search(low):
        conv["pending"] = None
        return "Okay, I haven't changed anything. What else can I help with?", []

    if re.search(r"\b(hi|hello|hey|namaste|vanakkam)\b", low) and len(low) < 25:
        return (f"Hello {actor.name.split()[0]}! I can show doctors, find free times, and book or cancel appointments. "
                "For example, say: book Dr Rao tomorrow at 10 AM for cataract."), []

    m = re.search(r"\bcancel\b.*?\b(a\d{1,6})\b", low)
    if m:
        appt_id = m[1].upper()
        try:
            appt = rules.check_cancel(s, actor, appt_id)
        except RuleError as e:
            return e.message, []
        conv["pending"] = {"action": "cancel", "args": {"appointment_id": appt_id}}
        return f"You want to cancel {appt_id} on {_d(appt.date)} at {_t12(appt.start_time)}. Shall I go ahead?", []
    if "cancel" in low:
        return "Please tell me the appointment number to cancel, like: cancel A012. Say 'my appointments' to hear them.", []

    if re.search(r"\b(my|show|list|upcoming)\b.*\bappointments?\b|\bappointments?\b.*\b(today|mine)\b", low):
        when = parse_date(low, today) if actor.role == "staff" else None
        items = services.list_appointments(s, actor, status="booked", date=when.isoformat() if when else None)
        items = [a for a in items if a["date"] >= today.isoformat()]
        if not items:
            return "There are no upcoming appointments.", []
        parts = [f"{a['id']} with {a['doctor_name']} on {_d(a['date'])} at {_t12(a['start_time'])}"
                 + (f" for {a['patient_name']}" if actor.role == "staff" else "") for a in items[:5]]
        more = f" And {len(items) - 5} more." if len(items) > 5 else ""
        return "Upcoming: " + "; ".join(parts) + "." + more, []

    doctor = find_doctor(s, low)
    spec = find_speciality(low)
    when = parse_date(low, today)
    at = parse_time(low)
    visit_type = "follow_up" if re.search(r"follow[\s-]?up|review", low) else "new"

    if re.search(r"\b(doctors?|who|which|speciali[sz]t)\b", low) and not re.search(r"\bbook\b", low) and not when:
        docs = services.list_doctors(s)
        if spec:
            docs = [d for d in docs if spec in d["specialities"]]
            if not docs:
                return f"Sorry, no doctor here covers {spec}.", []
            return f"For {spec} you can see " + " or ".join(d["name"] for d in docs) + ".", []
        return "Our doctors are " + "; ".join(f"{d['name']} for {', '.join(d['specialities'])}" for d in docs) + ".", []

    wants_book = bool(re.search(r"\b(book|appointment|schedule|reserve|fix)\b", low))
    wants_slots = bool(re.search(r"\b(free|slots?|available|availability|open|timings?)\b", low))

    if (wants_book or wants_slots) and not doctor:
        if spec:
            docs = [d for d in services.list_doctors(s) if spec in d["specialities"]]
            return f"For {spec}, which doctor would you like: " + " or ".join(d["name"] for d in docs) + "?", []
        return "Which doctor would you like? You can also tell me the problem, like cataract or glaucoma.", []

    if doctor and (wants_book or wants_slots or when):
        spec = spec if spec in doctor.speciality_list else doctor.speciality_list[0]
        if not when:
            return f"On which day would you like to see {doctor.name}?", []
        if wants_book and at and actor.role == "patient":
            args = {"patient_id": actor.id, "doctor_id": doctor.id, "speciality": spec, "visit_type": visit_type,
                    "date_str": when.isoformat(), "start_str": at}
            try:
                rules.check_booking(s, patient_id=actor.id, doctor_id=doctor.id, speciality=spec, visit_type=visit_type,
                                    date_str=when.isoformat(), start_str=at)
            except RuleError as e:
                alt = rules.free_slots(s, doctor.id, when.isoformat(), visit_type, spec)
                hint = f" Free times that day include {', '.join(_t12(x) for x in alt['slots'][:4])}." if alt["slots"] else ""
                return e.message + hint, []
            conv["pending"] = {"action": "book", "args": args}
            kind = "follow-up" if visit_type == "follow_up" else "new consultation"
            return (f"A {kind} for {spec} with {doctor.name} on {_d(when.isoformat())} at {_t12(at)}. "
                    "Shall I book it?"), []
        if wants_book and at and actor.role == "staff":
            return "For staff bookings with voice, please turn on AI mode, or use the Book for patient form.", []
        result = rules.free_slots(s, doctor.id, when.isoformat(), visit_type, spec)
        if not result["slots"]:
            return result["reason"] or "There are no free times that day.", []
        sample = ", ".join(_t12(x) for x in result["slots"][:6])
        return (f"{doctor.name} has {len(result['slots'])} free times on {_d(when.isoformat())}, "
                f"starting {sample}. Which time would you like?"), []

    return ("I can help with doctors, free times, booking and cancelling. Try: "
            "free slots with Dr Shah on Friday, or book Dr Rao tomorrow at 10 AM for cataract."), []
