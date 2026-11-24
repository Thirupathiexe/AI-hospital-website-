"""Request bodies. Pydantic rejects anything that doesn't match before our code sees it."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

NAME = r"^[A-Za-z][A-Za-z .'\-]{1,59}$"
MOBILE = r"^[0-9]{10}$"
DATE = r"^\d{4}-\d{2}-\d{2}$"
TIME = r"^\d{2}:\d{2}$"
DOCTOR_ID = r"^D\d{1,3}$"
PATIENT_ID = r"^P\d{1,5}$"
APPT_ID = r"^A\d{1,6}$"
SPECIALITY = Literal["Cataract", "General", "Glaucoma", "Retina", "Cornea", "Refractive", "Dry eye", "Paediatric", "Squint"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginIn(Strict):
    role: Literal["patient", "staff", "doctor"]
    name: Optional[str] = Field(default=None, pattern=NAME)
    mobile: Optional[str] = Field(default=None, pattern=MOBILE)
    doctor_id: Optional[str] = Field(default=None, pattern=DOCTOR_ID)
    access_code: Optional[str] = Field(default=None, max_length=64)


class BookIn(Strict):
    patient_id: Optional[str] = Field(default=None, pattern=PATIENT_ID)  # staff only; patients book for themselves
    doctor_id: str = Field(pattern=DOCTOR_ID)
    speciality: SPECIALITY
    visit_type: Literal["new", "follow_up"]
    date: str = Field(pattern=DATE)
    start_time: str = Field(pattern=TIME)


class RescheduleIn(Strict):
    doctor_id: str = Field(pattern=DOCTOR_ID)
    speciality: SPECIALITY
    visit_type: Literal["new", "follow_up"]
    date: str = Field(pattern=DATE)
    start_time: str = Field(pattern=TIME)


class PatientIn(Strict):
    name: str = Field(pattern=NAME)
    mobile: str = Field(pattern=MOBILE)
    year_of_birth: Optional[int] = Field(default=None, ge=1900, le=2100)


class ChatIn(Strict):
    message: str = Field(min_length=1, max_length=600)
    conversation_id: Optional[str] = Field(default=None, pattern=r"^[A-Za-z0-9_-]{8,64}$")
