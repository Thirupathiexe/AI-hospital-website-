"""Read-side helpers shared by the HTTP routes and the AI assistant tools.
Every function takes the Actor, so role limits apply no matter who calls."""
from __future__ import annotations

import re
from typing import Optional

from sqlmodel import Session, col, select

from . import rules
from .models import Appointment, AuditLog, Doctor, Patient, WeeklySchedule
from .rules import Actor, RuleError


def doctor_out(s: Session, d: Doctor) -> dict:
    sched = s.exec(select(WeeklySchedule).where(WeeklySchedule.doctor_id == d.id)).all()
    return {"id": d.id, "name": d.name, "specialities": d.speciality_list,
            "schedule": {f"{r.day}-{r.session}": r.status for r in sched}}


def list_doctors(s: Session) -> list[dict]:
    return [doctor_out(s, d) for d in s.exec(select(Doctor).order_by(Doctor.id)).all()]


def appointment_out(s: Session, a: Appointment, viewer: Actor) -> dict:
    doc = s.get(Doctor, a.doctor_id)
    pat = s.get(Patient, a.patient_id)
    out = {"id": a.id, "doctor_id": a.doctor_id, "doctor_name": doc.name if doc else a.doctor_id,
           "speciality": a.speciality, "visit_type": a.visit_type, "date": a.date,
           "start_time": a.start_time, "end_time": a.end_time, "status": a.status,
           "patient_id": a.patient_id, "patient_name": pat.name if pat else ""}
    if viewer.role == "staff" and pat:
        out["patient_mobile"] = pat.mobile  # only staff see contact details
    return out


def list_appointments(s: Session, viewer: Actor, *, date: Optional[str] = None, doctor_id: Optional[str] = None,
                      status: Optional[str] = None) -> list[dict]:
    q = select(Appointment)
    if viewer.role == "patient":
        q = q.where(Appointment.patient_id == viewer.id)  # patients only ever see their own
    elif viewer.role == "doctor":
        q = q.where(Appointment.doctor_id == viewer.id)
    elif doctor_id:
        q = q.where(Appointment.doctor_id == doctor_id)
    if date:
        q = q.where(Appointment.date == date)
    if status:
        q = q.where(Appointment.status == status)
    q = q.order_by(col(Appointment.date), col(Appointment.start_time))
    return [appointment_out(s, a, viewer) for a in s.exec(q).all()]


def normalise_name(name: str) -> str:
    return re.sub(r"\s+", " ", name or "").strip().lower()


def next_patient_id(s: Session) -> str:
    ids = s.exec(select(Patient.id)).all()
    nums = [int(i[1:]) for i in ids if i[1:].isdigit()]
    return f"P{(max(nums) + 1) if nums else 1:02d}"


def find_or_create_patient(s: Session, actor: Actor, name: str, mobile: str, year_of_birth: Optional[int] = None) -> tuple[Patient, bool]:
    existing = s.exec(select(Patient).where(Patient.mobile == mobile)).first()
    if existing:
        if normalise_name(existing.name) != normalise_name(name):
            raise RuleError("NAME_MISMATCH", "That mobile number is registered under a different name.", 401)
        return existing, False
    p = Patient(id=next_patient_id(s), name=re.sub(r"\s+", " ", name).strip(), mobile=mobile, year_of_birth=year_of_birth)
    s.add(p)
    s.add(AuditLog(actor_role=actor.role, actor_id=actor.id, action="create_patient", detail=p.id))
    s.commit()
    s.refresh(p)
    return p, True


def search_patients(s: Session, q: str) -> list[dict]:
    q = (q or "").strip()[:40]
    stmt = select(Patient).order_by(Patient.id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((col(Patient.name).ilike(like)) | (col(Patient.mobile).like(like)) | (col(Patient.id).ilike(like)))
    return [{"id": p.id, "name": p.name, "mobile": p.mobile, "year_of_birth": p.year_of_birth}
            for p in s.exec(stmt.limit(25)).all()]
