"""NetraCare API. Run with:  uvicorn app.main:app --reload  (from the backend folder)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from . import config, rules, services
from .assistant import agent as assistant_agent
from .db import get_session, init_db
from .models import AuditLog, Doctor, Holiday, Patient
from .rules import Actor, RuleError
from .schemas import BookIn, ChatIn, LoginIn, PatientIn, RescheduleIn
from .security import (COOKIE_NAME, BodySizeLimitMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware,
                       current_actor, make_token, require, safe_equals)

log = logging.getLogger("netracare")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="NetraCare API", version="1.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization"])


@app.middleware("http")
async def csrf_guard(request: Request, call_next):
    """Block cross-site form posts: state-changing calls must be JSON from an allowed origin."""
    if request.method == "POST" and request.url.path.startswith("/api"):
        origin = request.headers.get("origin")
        host_origin = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if origin and origin not in config.CORS_ORIGINS and origin != host_origin:
            return JSONResponse({"detail": {"code": "BAD_ORIGIN", "message": "Request blocked."}}, status_code=403)
        ctype = request.headers.get("content-type", "")
        if not ctype.startswith("application/json") and request.headers.get("content-length", "0") not in ("", "0"):
            return JSONResponse({"detail": {"code": "BAD_CONTENT_TYPE", "message": "Send JSON."}}, status_code=415)
    return await call_next(request)


# ---------- error handling: clear messages, never internals ----------

@app.exception_handler(RuleError)
async def rule_error_handler(_: Request, exc: RuleError):
    return JSONResponse({"detail": {"code": exc.code, "message": exc.message}}, status_code=exc.status)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    fields = ", ".join(str(e["loc"][-1]) for e in exc.errors())
    return JSONResponse({"detail": {"code": "INVALID_INPUT", "message": f"Please check: {fields}."}}, status_code=422)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error")
    return JSONResponse({"detail": {"code": "SERVER_ERROR", "message": "Something went wrong. Please try again."}}, status_code=500)


# ---------- auth ----------

@app.post("/api/login")
def login(body: LoginIn, response: Response, s: Session = Depends(get_session)):
    if body.role == "patient":
        if not body.mobile or not body.name:
            raise RuleError("INVALID_INPUT", "Please enter your mobile number and name.", 422)
        patient, created = services.find_or_create_patient(s, Actor("patient", "self"), body.name, body.mobile)
        actor = Actor("patient", patient.id, patient.name)
    elif body.role == "doctor":
        if config.DOCTOR_ACCESS_CODE and not safe_equals(body.access_code or "", config.DOCTOR_ACCESS_CODE):
            raise RuleError("BAD_ACCESS_CODE", "Access code is not correct.", 401)
        doc = s.get(Doctor, body.doctor_id or "")
        if not doc:
            raise RuleError("UNKNOWN_DOCTOR", "Please pick your name from the list.", 422)
        actor, created = Actor("doctor", doc.id, doc.name), False
    else:
        if not body.name:
            raise RuleError("INVALID_INPUT", "Please enter your name.", 422)
        if config.STAFF_ACCESS_CODE and not safe_equals(body.access_code or "", config.STAFF_ACCESS_CODE):
            raise RuleError("BAD_ACCESS_CODE", "Access code is not correct.", 401)
        actor, created = Actor("staff", body.name, body.name), False

    token = make_token(actor)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="strict", secure=config.COOKIE_SECURE,
                        max_age=config.TOKEN_TTL_MINUTES * 60, path="/")
    s.add(AuditLog(actor_role=actor.role, actor_id=actor.id, action="login"))
    s.commit()
    # The token is also returned for API/agent clients that use a Bearer header. The website uses the cookie.
    return {"role": actor.role, "id": actor.id, "name": actor.name, "new_patient": created, "token": token}


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/me")
def me(actor: Actor = Depends(current_actor)):
    return {"role": actor.role, "id": actor.id, "name": actor.name}


# ---------- public clinic info ----------

@app.get("/api/clock")
def clock():
    n = config.now()
    return {"now": n.strftime("%Y-%m-%d %H:%M"), "today": n.date().isoformat(), "window_days": config.BOOKING_WINDOW_DAYS}


@app.get("/api/doctors")
def doctors(s: Session = Depends(get_session)):
    return services.list_doctors(s)


@app.get("/api/holidays")
def holidays(s: Session = Depends(get_session)):
    return [{"date": h.date, "name": h.name} for h in s.exec(select(Holiday).order_by(Holiday.date)).all()]


# ---------- slots and appointments ----------

@app.get("/api/slots")
def slots(doctor_id: str = Query(pattern=r"^D\d{1,3}$"), date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
          visit_type: Literal["new", "follow_up"] = "new", speciality: Optional[str] = Query(default=None, max_length=30),
          _: Actor = Depends(current_actor), s: Session = Depends(get_session)):
    return rules.free_slots(s, doctor_id, date, visit_type, speciality)


@app.get("/api/appointments")
def appointments(date: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
                 doctor_id: Optional[str] = Query(default=None, pattern=r"^D\d{1,3}$"),
                 status: Optional[Literal["booked", "cancelled", "completed"]] = None,
                 actor: Actor = Depends(current_actor), s: Session = Depends(get_session)):
    return services.list_appointments(s, actor, date=date, doctor_id=doctor_id, status=status)


@app.post("/api/appointments", status_code=201)
def create_appointment(body: BookIn, actor: Actor = Depends(require("patient", "staff")), s: Session = Depends(get_session)):
    patient_id = actor.id if actor.role == "patient" else body.patient_id
    if not patient_id:
        raise RuleError("INVALID_INPUT", "Please choose the patient.", 422)
    appt = rules.book(s, actor, patient_id=patient_id, doctor_id=body.doctor_id, speciality=body.speciality,
                      visit_type=body.visit_type, date_str=body.date, start_str=body.start_time)
    return services.appointment_out(s, appt, actor)


@app.post("/api/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: str, actor: Actor = Depends(require("patient", "staff")), s: Session = Depends(get_session)):
    appt = rules.cancel(s, actor, appointment_id[:10])
    return services.appointment_out(s, appt, actor)


@app.post("/api/appointments/{appointment_id}/reschedule")
def reschedule_appointment(appointment_id: str, body: RescheduleIn, actor: Actor = Depends(require("patient", "staff")),
                           s: Session = Depends(get_session)):
    appt = rules.reschedule(s, actor, appointment_id[:10], doctor_id=body.doctor_id, speciality=body.speciality,
                            visit_type=body.visit_type, date_str=body.date, start_str=body.start_time)
    return services.appointment_out(s, appt, actor)


@app.post("/api/appointments/{appointment_id}/complete")
def complete_appointment(appointment_id: str, actor: Actor = Depends(require("doctor")), s: Session = Depends(get_session)):
    appt = rules.complete(s, actor, appointment_id[:10])
    return services.appointment_out(s, appt, actor)


# ---------- staff: patients ----------

@app.get("/api/patients")
def patients(q: str = Query(default="", max_length=40), _: Actor = Depends(require("staff")), s: Session = Depends(get_session)):
    return services.search_patients(s, q)


@app.post("/api/patients", status_code=201)
def add_patient(body: PatientIn, actor: Actor = Depends(require("staff")), s: Session = Depends(get_session)):
    p, created = services.find_or_create_patient(s, actor, body.name, body.mobile, body.year_of_birth)
    return {"id": p.id, "name": p.name, "mobile": p.mobile, "created": created}


# ---------- AI voice assistant ----------

@app.post("/api/assistant/chat")
def assistant_chat(body: ChatIn, actor: Actor = Depends(require("patient", "staff")), s: Session = Depends(get_session)):
    return assistant_agent.chat(s, actor, body.message, body.conversation_id)


@app.get("/api/assistant/status")
def assistant_status():
    return {"ai": assistant_agent.ai_available()}


# ---------- serve the built React site (production) ----------

DIST = config.BASE_DIR.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = (DIST / path).resolve()
        if path and target.is_file() and DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(DIST / "index.html")
