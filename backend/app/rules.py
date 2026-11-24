"""THE one place where clinic rules live.

Every booking, cancel, reschedule and completion — from the website, from /docs,
or from the AI voice assistant — goes through the functions in this file.
A broken rule raises RuleError(code, message). Codes match the data pack README.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlmodel import Session, col, select

from . import config
from .models import Appointment, AuditLog, Doctor, Holiday, Patient, WeeklySchedule

DURATION_MIN = {"new": 20, "follow_up": 10}
SESSIONS = {"AM": (time(9, 0), time(13, 0)), "PM": (time(14, 0), time(18, 0))}
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FULL_DAY = ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"]

# One lock around "check + write" so two people can never grab the same slot at once.
_write_lock = threading.Lock()


class RuleError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


@dataclass
class Actor:
    role: str  # patient / staff / doctor
    id: str  # patient id, doctor id, or staff name
    name: str = ""


# ---------- small helpers ----------

def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise RuleError("INVALID_INPUT", "Please give the date as YYYY-MM-DD.", 422)


def parse_time(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError):
        raise RuleError("INVALID_INPUT", "Please give the time as HH:MM (24-hour).", 422)


def fmt12(t: time) -> str:
    return datetime.combine(date.today(), t).strftime("%I:%M %p").lstrip("0")


def add_minutes(t: time, minutes: int) -> time:
    return (datetime.combine(date.today(), t) + timedelta(minutes=minutes)).time()


def session_of(t: time) -> Optional[str]:
    for name, (start, end) in SESSIONS.items():
        if start <= t < end:
            return name
    return None


def get_doctor(s: Session, doctor_id: str) -> Doctor:
    doc = s.get(Doctor, doctor_id)
    if not doc:
        raise RuleError("UNKNOWN_DOCTOR", "We couldn't find that doctor.", 404)
    return doc


def doctor_status(s: Session, doctor_id: str, d: date, sess: str) -> str:
    row = s.exec(select(WeeklySchedule).where(
        WeeklySchedule.doctor_id == doctor_id,
        WeeklySchedule.day == DAY_NAMES[d.weekday()],
        WeeklySchedule.session == sess)).first()
    return row.status if row else "OFF"


def audit(s: Session, actor: Actor, action: str, detail: str) -> None:
    s.add(AuditLog(actor_role=actor.role, actor_id=actor.id, action=action, detail=detail[:500]))


def _overlaps(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    return a_start < b_end and b_start < a_end


# ---------- day-level checks (used by booking and by the free-slot list) ----------

def check_day(s: Session, doctor: Doctor, d: date, now: datetime) -> None:
    today = now.date()
    if d < today:
        raise RuleError("IN_PAST", "That date has already passed. Please pick a future date.")
    if d > today + timedelta(days=config.BOOKING_WINDOW_DAYS):
        raise RuleError("BEYOND_30_DAYS", f"Bookings open only {config.BOOKING_WINDOW_DAYS} days ahead. Please pick a date on or before {(today + timedelta(days=config.BOOKING_WINDOW_DAYS)).strftime('%d %b %Y')}.")
    if d.weekday() == 6:
        raise RuleError("CLINIC_CLOSED", "The clinic is closed on Sundays.")
    hol = s.get(Holiday, d.isoformat())
    if hol:
        raise RuleError("HOLIDAY", f"The clinic is closed on {d.strftime('%d %b %Y')} ({hol.name}).")


def check_session(s: Session, doctor: Doctor, d: date, sess: str) -> None:
    status = doctor_status(s, doctor.id, d, sess)
    part = "mornings" if sess == "AM" else "afternoons"
    if status == "SURGERY":
        raise RuleError("SURGERY_SESSION", f"{doctor.name} is in surgery on {d.strftime('%A')} {part}, so there is no OPD then.")
    if status != "OPD":
        when = FULL_DAY[d.weekday()] if doctor_status(s, doctor.id, d, "AM" if sess == "PM" else "PM") != "OPD" else f"{d.strftime('%A')} {part}"
        raise RuleError("DOCTOR_OFF", f"{doctor.name} is not at the clinic on {when}.")


# ---------- the main booking check ----------

def check_booking(s: Session, *, patient_id: Optional[str], doctor_id: str, speciality: str, visit_type: str,
                  date_str: str, start_str: str, ignore_appointment_id: Optional[str] = None,
                  now: Optional[datetime] = None) -> tuple[date, time, time]:
    """Raise RuleError if this booking breaks any clinic rule. Returns (date, start, end).
    patient_id=None skips the per-patient rules (used to list free slots)."""
    now = now or config.now()
    if visit_type not in DURATION_MIN:
        raise RuleError("INVALID_INPUT", "Visit type must be 'new' or 'follow_up'.", 422)
    d = parse_date(date_str)
    start = parse_time(start_str)
    end = add_minutes(start, DURATION_MIN[visit_type])
    doctor = get_doctor(s, doctor_id)

    if start.minute % 10 != 0:
        raise RuleError("INVALID_START_TIME", "Appointments start on 10-minute marks, like 10:00 or 10:10.")
    if datetime.combine(d, start) < now:
        raise RuleError("IN_PAST", "That time has already passed. Please pick a later time.")
    check_day(s, doctor, d, now)

    sess = session_of(start)
    if sess is None:
        raise RuleError("OUTSIDE_SESSION", "The clinic is closed at that time. OPD runs 9 AM–1 PM and 2 PM–6 PM.")
    sess_end = SESSIONS[sess][1]
    if end > sess_end:
        raise RuleError("ENDS_AFTER_SESSION", f"A {DURATION_MIN[visit_type]}-minute visit at {fmt12(start)} would end after {fmt12(sess_end)}. Please pick an earlier time.")
    check_session(s, doctor, d, sess)

    if speciality not in doctor.speciality_list:
        raise RuleError("SPECIALITY_MISMATCH", f"{doctor.name} does not cover {speciality}. They cover {', '.join(doctor.speciality_list)}.")

    s_str, e_str = start.strftime("%H:%M"), end.strftime("%H:%M")
    same_day = s.exec(select(Appointment).where(Appointment.date == d.isoformat(), Appointment.status == "booked")).all()
    for a in same_day:
        if a.id != ignore_appointment_id and a.doctor_id == doctor_id and _overlaps(s_str, e_str, a.start_time, a.end_time):
            raise RuleError("DOUBLE_BOOKED", f"{doctor.name} is already booked at {fmt12(start)}. Please choose another time.")

    if patient_id is not None:
        if not s.get(Patient, patient_id):
            raise RuleError("UNKNOWN_PATIENT", "We couldn't find that patient.", 404)
        for a in same_day:
            if a.id != ignore_appointment_id and a.patient_id == patient_id and _overlaps(s_str, e_str, a.start_time, a.end_time):
                raise RuleError("PATIENT_OVERLAP", "This patient already has another appointment at that time.")

        active = s.exec(select(Appointment).where(
            Appointment.patient_id == patient_id, Appointment.speciality == speciality,
            Appointment.status == "booked")).all()
        for a in active:
            if a.id == ignore_appointment_id:
                continue
            if datetime.combine(parse_date(a.date), parse_time(a.end_time)) >= now:
                raise RuleError("ACTIVE_BOOKING_EXISTS", f"There is already a {speciality} appointment booked ({a.id} on {a.date} at {a.start_time}). Only one active booking per speciality is allowed.")

        if visit_type == "follow_up":
            last = s.exec(select(Appointment).where(
                Appointment.patient_id == patient_id, Appointment.speciality == speciality,
                Appointment.status == "completed").order_by(col(Appointment.date).desc(), col(Appointment.start_time).desc())).first()
            if not last:
                raise RuleError("NO_PREVIOUS_VISIT", f"A follow-up needs a completed {speciality} visit first. Please book a new consultation instead.")
            if last.doctor_id != doctor_id:
                seen_by = s.get(Doctor, last.doctor_id)
                raise RuleError("FOLLOW_UP_DIFFERENT_DOCTOR", f"A {speciality} follow-up must be with {seen_by.name if seen_by else 'the doctor who saw you last'}, who saw this patient last.")
    return d, start, end


def _next_id(s: Session) -> str:
    ids = s.exec(select(Appointment.id)).all()
    nums = [int(i[1:]) for i in ids if i[1:].isdigit()]
    return f"A{(max(nums) + 1) if nums else 1:03d}"


# ---------- actions ----------

def book(s: Session, actor: Actor, *, patient_id: str, doctor_id: str, speciality: str, visit_type: str,
         date_str: str, start_str: str) -> Appointment:
    if actor.role == "patient" and patient_id != actor.id:
        raise RuleError("NOT_YOUR_APPOINTMENT", "Patients can only book for themselves.", 403)
    if actor.role not in ("patient", "staff"):
        raise RuleError("FORBIDDEN", "Only patients and staff can book appointments.", 403)
    with _write_lock:
        d, start, end = check_booking(s, patient_id=patient_id, doctor_id=doctor_id, speciality=speciality,
                                      visit_type=visit_type, date_str=date_str, start_str=start_str)
        appt = Appointment(id=_next_id(s), patient_id=patient_id, doctor_id=doctor_id, speciality=speciality,
                           visit_type=visit_type, date=d.isoformat(), start_time=start.strftime("%H:%M"),
                           end_time=end.strftime("%H:%M"), booked_by=actor.role)
        s.add(appt)
        audit(s, actor, "book", f"{appt.id} {patient_id} {doctor_id} {appt.date} {appt.start_time}")
        s.commit()
        s.refresh(appt)
        return appt


def check_cancel(s: Session, actor: Actor, appointment_id: str, now: Optional[datetime] = None) -> Appointment:
    now = now or config.now()
    appt = s.get(Appointment, appointment_id)
    if actor.role == "patient":
        if not appt or appt.patient_id != actor.id:
            raise RuleError("NOT_YOUR_APPOINTMENT", "That appointment is not yours.", 403)
    elif actor.role != "staff":
        raise RuleError("FORBIDDEN", "Only patients and staff can cancel appointments.", 403)
    if not appt:
        raise RuleError("NOT_FOUND", "We couldn't find that appointment.", 404)
    if appt.status != "booked":
        raise RuleError("NOT_ACTIVE", f"This appointment is already {appt.status}.")
    if actor.role == "patient":
        starts = datetime.combine(parse_date(appt.date), parse_time(appt.start_time))
        if starts - now < timedelta(hours=config.PATIENT_CANCEL_CUTOFF_HOURS):
            raise RuleError("INSIDE_2_HOURS", "This appointment starts in less than 2 hours. Please contact Staff to cancel or change it.")
    return appt


def cancel(s: Session, actor: Actor, appointment_id: str) -> Appointment:
    with _write_lock:
        appt = check_cancel(s, actor, appointment_id)
        appt.status = "cancelled"
        appt.cancelled_by = actor.role
        audit(s, actor, "cancel", appt.id)
        s.commit()
        s.refresh(appt)
        return appt


def reschedule(s: Session, actor: Actor, appointment_id: str, *, doctor_id: str, speciality: str, visit_type: str,
               date_str: str, start_str: str) -> Appointment:
    """Cancel + new booking, as one step. If the new booking is refused, the original stays."""
    with _write_lock:
        old = check_cancel(s, actor, appointment_id)
        d, start, end = check_booking(s, patient_id=old.patient_id, doctor_id=doctor_id, speciality=speciality,
                                      visit_type=visit_type, date_str=date_str, start_str=start_str,
                                      ignore_appointment_id=old.id)
        old.status = "cancelled"
        old.cancelled_by = actor.role
        new = Appointment(id=_next_id(s), patient_id=old.patient_id, doctor_id=doctor_id, speciality=speciality,
                          visit_type=visit_type, date=d.isoformat(), start_time=start.strftime("%H:%M"),
                          end_time=end.strftime("%H:%M"), booked_by=actor.role)
        s.add(new)
        audit(s, actor, "reschedule", f"{old.id} -> {new.id}")
        s.commit()
        s.refresh(new)
        return new


def complete(s: Session, actor: Actor, appointment_id: str) -> Appointment:
    if actor.role != "doctor":
        raise RuleError("FORBIDDEN", "Only the doctor can mark a visit as completed.", 403)
    with _write_lock:
        appt = s.get(Appointment, appointment_id)
        if not appt or appt.doctor_id != actor.id:
            raise RuleError("NOT_YOUR_APPOINTMENT", "That appointment is not on your schedule.", 403)
        if appt.status != "booked":
            raise RuleError("NOT_ACTIVE", f"This appointment is already {appt.status}.")
        if parse_date(appt.date) > config.now().date():
            raise RuleError("NOT_YET", "You can mark a visit completed on or after the visit day.")
        appt.status = "completed"
        audit(s, actor, "complete", appt.id)
        s.commit()
        s.refresh(appt)
        return appt


def free_slots(s: Session, doctor_id: str, date_str: str, visit_type: str, speciality: Optional[str] = None) -> dict:
    """Start times that can be booked. Same rules as booking, minus the per-patient ones."""
    doctor = get_doctor(s, doctor_id)
    d = parse_date(date_str)
    now = config.now()
    try:
        check_day(s, doctor, d, now)
    except RuleError as e:
        return {"slots": [], "reason": e.message, "code": e.code}
    spec = speciality or doctor.speciality_list[0]
    if spec not in doctor.speciality_list:
        return {"slots": [], "reason": f"{doctor.name} does not cover {spec}.", "code": "SPECIALITY_MISMATCH"}

    slots, reasons = [], []
    for sess, (start, end) in SESSIONS.items():
        try:
            check_session(s, doctor, d, sess)
        except RuleError as e:
            reasons.append(e.message)
            continue
        t = start
        while t < end:
            try:
                check_booking(s, patient_id=None, doctor_id=doctor_id, speciality=spec, visit_type=visit_type,
                              date_str=date_str, start_str=t.strftime("%H:%M"), now=now)
                slots.append(t.strftime("%H:%M"))
            except RuleError:
                pass
            t = add_minutes(t, 10)
    reason = None if slots else (" ".join(reasons) or "All slots on this day are taken.")
    return {"slots": slots, "reason": reason, "code": None}
