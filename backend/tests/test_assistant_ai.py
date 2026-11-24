"""Tests the AI tool loop with a fake Claude client (no API key or network needed)."""
from types import SimpleNamespace as NS

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.assistant import agent
from app.db import load_data_pack
from app.rules import Actor


class FakeMessages:
    def __init__(self, script):
        self.script, self.calls = script, []

    def create(self, **kw):
        self.calls.append(kw)
        return self.script.pop(0)


def tool_use(id_, name, inp):
    return NS(type="tool_use", id=id_, name=name, input=inp)


def test_ai_books_through_rules(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    script = [
        NS(stop_reason="tool_use", content=[tool_use("t1", "book_appointment", {
            "doctor_id": "D2", "speciality": "Glaucoma", "visit_type": "new", "date": "2026-11-05",
            "start_time": "10:00", "user_confirmed": True})]),  # Thursday: Dr. Iyer is off -> refused
        NS(stop_reason="tool_use", content=[tool_use("t2", "book_appointment", {
            "doctor_id": "D2", "speciality": "Glaucoma", "visit_type": "new", "date": "2026-11-04",
            "start_time": "10:00", "user_confirmed": True, "patient_id": "P01"})]),  # patient_id ignored for patients
        NS(stop_reason="end_turn", content=[NS(type="text", text="Booked for Wednesday at 10 AM.")]),
    ]
    fake = FakeMessages(script)
    monkeypatch.setattr(agent, "ai_available", lambda: True)
    monkeypatch.setattr(agent, "_get_client", lambda: NS(beta=NS(messages=fake)))
    with Session(engine) as s:
        load_data_pack(s)
        out = agent.chat(s, Actor("patient", "P05", "Priya"), "book Dr Iyer", None)
    assert out["mode"] == "ai" and out["reply"].startswith("Booked")
    assert out["actions"][0]["appointment"]["patient_id"] == "P05"  # acted only as the logged-in patient
    results = [b for m in fake.calls[-1]["messages"] if m["role"] == "user" and isinstance(m["content"], list)
               for b in m["content"]]
    refused = results[0]
    assert refused["is_error"] and "DOCTOR_OFF" in refused["content"]
    assert fake.calls[0]["model"] == "claude-opus-5-5" and fake.calls[0]["fallbacks"] == "default"
