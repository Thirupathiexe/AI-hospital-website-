"""Runs the 38 cases in data/stretch/rule_tests.csv. Each test starts from a fresh copy of the seed data."""
import csv

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import config, rules
from app.db import load_data_pack
from app.models import Appointment
from app.rules import Actor, RuleError

CASES = list(csv.DictReader((config.DATA_DIR / "stretch" / "rule_tests.csv").open(encoding="utf-8")))


@pytest.fixture
def s():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        load_data_pack(session, with_seed=True)
        yield session


def run_case(s, c):
    actor = Actor(c["role"], c["acting_patient_id"] if c["role"] == "patient" else "Front Desk")
    if c["action"] == "book":
        return rules.book(s, actor, patient_id=c["acting_patient_id"], doctor_id=c["doctor_id"], speciality=c["speciality"],
                          visit_type=c["visit_type"], date_str=c["date"], start_str=c["start_time"])
    if c["action"] == "cancel":
        return rules.cancel(s, actor, c["appointment_id"])
    return rules.reschedule(s, actor, c["appointment_id"], doctor_id=c["doctor_id"], speciality=c["speciality"],
                            visit_type=c["visit_type"], date_str=c["date"], start_str=c["start_time"])


@pytest.mark.parametrize("c", CASES, ids=[c["test_id"] for c in CASES])
def test_rule_case(s, c):
    before = s.get(Appointment, c["appointment_id"]).status if c["appointment_id"] else None
    if c["expected"] == "allowed":
        appt = run_case(s, c)
        if c["action"] == "cancel":
            assert appt.status == "cancelled"
        else:
            assert appt.status == "booked"
            expected_len = 20 if c["visit_type"] == "new" else 10
            assert rules.add_minutes(rules.parse_time(appt.start_time), expected_len).strftime("%H:%M") == appt.end_time
    else:  # refused, or to_staff (no approval queue -> refused with "Please contact Staff")
        with pytest.raises(RuleError) as err:
            run_case(s, c)
        assert err.value.code == c["reason_code"], err.value.message
        if c["expected"] == "to_staff":
            assert "contact Staff" in err.value.message
        if before:  # a refused cancel/reschedule leaves the original untouched
            s.expire_all()
            assert s.get(Appointment, c["appointment_id"]).status == before


def test_slots_thursday_morning_rao(s):
    out = rules.free_slots(s, "D1", "2026-11-05", "new")
    assert all(t >= "14:00" for t in out["slots"]) and out["slots"]


def test_slot_disappears_once_booked(s):
    assert "09:20" in rules.free_slots(s, "D1", "2026-11-04", "new")["slots"]
    rules.book(s, Actor("patient", "P17"), patient_id="P17", doctor_id="D1", speciality="Cataract",
               visit_type="new", date_str="2026-11-04", start_str="09:20")
    slots = rules.free_slots(s, "D1", "2026-11-04", "new")["slots"]
    assert "09:20" not in slots and "09:10" not in slots  # 09:10 would overlap too


def test_follow_up_after_completion(s):
    p = Actor("patient", "P17")
    appt = rules.book(s, p, patient_id="P17", doctor_id="D1", speciality="Cataract", visit_type="new",
                      date_str="2026-11-02", start_str="11:00")
    with pytest.raises(RuleError):
        rules.complete(s, Actor("doctor", "D2"), appt.id)  # not Dr. Iyer's patient
    rules.complete(s, Actor("doctor", "D1"), appt.id)
    with pytest.raises(RuleError) as e:
        rules.book(s, p, patient_id="P17", doctor_id="D2", speciality="Cataract", visit_type="follow_up",
                   date_str="2026-11-04", start_str="11:00")
    assert e.value.code == "FOLLOW_UP_DIFFERENT_DOCTOR"
    rules.book(s, p, patient_id="P17", doctor_id="D1", speciality="Cataract", visit_type="follow_up",
               date_str="2026-11-04", start_str="11:00")
