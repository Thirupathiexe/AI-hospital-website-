"""Tools the AI assistant can use. Each one calls the SAME rules and services as the website,
acting as the logged-in user — so the AI can never do more than that user could do by hand."""
from __future__ import annotations

import json
from typing import Any

from sqlmodel import Session

from .. import rules, services
from ..rules import Actor, RuleError

SPECIALITIES = ["Cataract", "General", "Glaucoma", "Retina", "Cornea", "Refractive", "Dry eye", "Paediatric", "Squint"]

TOOLS: list[dict] = [
    {"name": "list_doctors", "description": "List all doctors, their specialities and weekly OPD/surgery/off schedule.",
     "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_free_slots",
     "description": "List bookable start times (HH:MM, 24h) for one doctor on one date. Call before proposing any time.",
     "input_schema": {"type": "object", "additionalProperties": False, "required": ["doctor_id", "date", "visit_type"],
                      "properties": {"doctor_id": {"type": "string", "description": "e.g. D1"},
                                     "date": {"type": "string", "description": "YYYY-MM-DD"},
                                     "visit_type": {"type": "string", "enum": ["new", "follow_up"]},
                                     "speciality": {"type": "string", "enum": SPECIALITIES}}}},
    {"name": "list_appointments",
     "description": "List appointments the current user is allowed to see (a patient sees only their own). Staff may filter by date/doctor.",
     "input_schema": {"type": "object", "additionalProperties": False,
                      "properties": {"date": {"type": "string"}, "doctor_id": {"type": "string"},
                                     "status": {"type": "string", "enum": ["booked", "cancelled", "completed"]}}}},
    {"name": "book_appointment",
     "description": "Book an appointment. Only call after the user has clearly said yes to the exact doctor, date, time, speciality and visit type. Staff must pass patient_id.",
     "input_schema": {"type": "object", "additionalProperties": False,
                      "required": ["doctor_id", "speciality", "visit_type", "date", "start_time", "user_confirmed"],
                      "properties": {"doctor_id": {"type": "string"}, "speciality": {"type": "string", "enum": SPECIALITIES},
                                     "visit_type": {"type": "string", "enum": ["new", "follow_up"]},
                                     "date": {"type": "string", "description": "YYYY-MM-DD"},
                                     "start_time": {"type": "string", "description": "HH:MM 24h"},
                                     "patient_id": {"type": "string", "description": "Staff only"},
                                     "user_confirmed": {"type": "boolean", "description": "true only if the user explicitly confirmed"}}}},
    {"name": "cancel_appointment",
     "description": "Cancel an appointment by id (e.g. A012). Only call after the user has clearly confirmed which appointment to cancel.",
     "input_schema": {"type": "object", "additionalProperties": False, "required": ["appointment_id", "user_confirmed"],
                      "properties": {"appointment_id": {"type": "string"}, "user_confirmed": {"type": "boolean"}}}},
    {"name": "find_patient", "description": "Staff only: search patients by name, mobile or id.",
     "input_schema": {"type": "object", "additionalProperties": False, "required": ["query"],
                      "properties": {"query": {"type": "string"}}}},
]


def _str(args: dict, key: str, max_len: int = 20) -> str:
    v = args.get(key)
    if not isinstance(v, str) or len(v) > max_len:
        raise RuleError("INVALID_INPUT", f"Missing or invalid '{key}'.", 422)
    return v.strip()


def run_tool(s: Session, actor: Actor, name: str, args: Any) -> tuple[str, bool, dict | None]:
    """Returns (json_text, is_error, action_event). action_event tells the UI something changed."""
    if not isinstance(args, dict):
        return json.dumps({"error": "INVALID_JSON"}), True, None
    try:
        if name == "list_doctors":
            data = services.list_doctors(s)
            return json.dumps(data), False, None
        if name == "get_free_slots":
            data = rules.free_slots(s, _str(args, "doctor_id"), _str(args, "date"), _str(args, "visit_type"),
                                    args.get("speciality"))
            return json.dumps(data), False, None
        if name == "list_appointments":
            data = services.list_appointments(s, actor, date=args.get("date"), doctor_id=args.get("doctor_id"),
                                              status=args.get("status"))
            return json.dumps(data[-30:]), False, None
        if name == "book_appointment":
            if args.get("user_confirmed") is not True:
                return json.dumps({"error": "NEEDS_CONFIRMATION", "message": "Ask the user to confirm first."}), True, None
            patient_id = actor.id if actor.role == "patient" else _str(args, "patient_id")
            appt = rules.book(s, actor, patient_id=patient_id, doctor_id=_str(args, "doctor_id"),
                              speciality=_str(args, "speciality"), visit_type=_str(args, "visit_type"),
                              date_str=_str(args, "date"), start_str=_str(args, "start_time"))
            out = services.appointment_out(s, appt, actor)
            return json.dumps({"booked": out}), False, {"type": "booked", "appointment": out}
        if name == "cancel_appointment":
            if args.get("user_confirmed") is not True:
                return json.dumps({"error": "NEEDS_CONFIRMATION", "message": "Ask the user to confirm first."}), True, None
            appt = rules.cancel(s, actor, _str(args, "appointment_id"))
            out = services.appointment_out(s, appt, actor)
            return json.dumps({"cancelled": out}), False, {"type": "cancelled", "appointment": out}
        if name == "find_patient":
            if actor.role != "staff":
                raise RuleError("FORBIDDEN", "Only staff can search patients.", 403)
            return json.dumps(services.search_patients(s, _str(args, "query", 40))), False, None
        return json.dumps({"error": "UNKNOWN_TOOL"}), True, None
    except RuleError as e:
        s.rollback()
        return json.dumps({"refused": True, "code": e.code, "message": e.message}), True, None
