"""Checks that roles are enforced by the backend, not just hidden by the screen."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.assistant.safety import red_flag_reply


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def login(client, **body):
    r = client.post("/api/login", json=body)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_r1_loaded(client):
    h = login(client, role="patient", mobile="9000000001", name="Asha Verma")
    assert len(client.get("/api/doctors", headers=h).json()) == 5


def test_name_mismatch_refused(client):
    r = client.post("/api/login", json={"role": "patient", "mobile": "9000000001", "name": "Someone Else"})
    assert r.status_code == 401


def test_patient_cannot_see_or_cancel_others(client):
    asha = login(client, role="patient", mobile="9000000001", name="Asha Verma")
    rohan = login(client, role="patient", mobile="9000000002", name="Rohan Gupta")
    r = client.post("/api/appointments", headers=asha, json={"doctor_id": "D3", "speciality": "Retina", "visit_type": "new",
                                                             "date": "2026-11-04", "start_time": "10:00"})
    assert r.status_code == 201, r.text
    appt_id = r.json()["id"]
    assert all(a["patient_id"] == "P02" for a in client.get("/api/appointments", headers=rohan).json())
    r = client.post(f"/api/appointments/{appt_id}/cancel", headers=rohan)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "NOT_YOUR_APPOINTMENT"
    # A patient can't book for someone else by sending patient_id
    r = client.post("/api/appointments", headers=rohan, json={"patient_id": "P01", "doctor_id": "D3", "speciality": "General",
                                                              "visit_type": "new", "date": "2026-11-04", "start_time": "11:00"})
    assert r.status_code == 201 and r.json()["patient_id"] == "P02"


def test_role_limits(client):
    patient = login(client, role="patient", mobile="9000000003", name="Lakshmi Nair")
    assert client.get("/api/patients", headers=patient).status_code == 403
    assert client.post("/api/appointments/A001/complete", headers=patient).status_code == 403
    doctor = login(client, role="doctor", doctor_id="D1")
    r = client.post("/api/appointments", headers=doctor, json={"patient_id": "P01", "doctor_id": "D1", "speciality": "General",
                                                               "visit_type": "new", "date": "2026-11-04", "start_time": "10:00"})
    assert r.status_code == 403


def test_tampered_token_rejected(client):
    h = login(client, role="patient", mobile="9000000004", name="Imran Sheikh")
    token = h["Authorization"].split()[1]
    body, sig = token.split(".")
    forged = {"Authorization": f"Bearer {body[:-2]}xx.{sig}"}
    assert client.get("/api/me", headers=forged).status_code == 401
    client.cookies.clear()
    assert client.get("/api/appointments").status_code == 401


def test_bad_input_rejected(client):
    r = client.post("/api/login", json={"role": "patient", "mobile": "12345", "name": "<script>"})
    assert r.status_code == 422
    r = client.post("/api/login", json={"role": "staff", "name": "Desk", "is_admin": True})
    assert r.status_code == 422


def test_cross_site_post_blocked(client):
    r = client.post("/api/login", json={"role": "staff", "name": "Desk"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_security_headers(client):
    r = client.get("/api/clock")
    assert r.headers["x-frame-options"] == "DENY" and "default-src 'none'" in r.headers["content-security-policy"]


def test_red_flags():
    assert red_flag_reply("I suddenly lost vision in my left eye")
    assert red_flag_reply("chemical splashed in my eye")
    assert red_flag_reply("my sight went dark suddenly")
    assert red_flag_reply("a curtain over my vision")
    for ok in ["book a cataract checkup", "my eyes are dry and itchy", "book Dr Iyer on friday at 11 am for glaucoma"]:
        assert red_flag_reply(ok) is None


def test_basic_assistant_books_with_confirmation(client):
    h = login(client, role="patient", mobile="9111111111", name="Test Voice")
    r = client.post("/api/assistant/chat", headers=h, json={"message": "book Dr Shah on wednesday at 10:30 am for retina"}).json()
    assert "Shall I book" in r["reply"], r
    r2 = client.post("/api/assistant/chat", headers=h, json={"message": "yes", "conversation_id": r["conversation_id"]}).json()
    assert r2["actions"] and r2["actions"][0]["type"] == "booked", r2
