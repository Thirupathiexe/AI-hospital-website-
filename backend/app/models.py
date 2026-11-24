"""Database tables (SQLModel on SQLite)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Doctor(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    specialities: str  # ";"-separated, as in doctors.csv

    @property
    def speciality_list(self) -> list[str]:
        return [s.strip() for s in self.specialities.split(";") if s.strip()]


class WeeklySchedule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    doctor_id: str = Field(foreign_key="doctor.id", index=True)
    day: str  # Mon..Sat
    session: str  # AM / PM
    status: str  # OPD / SURGERY / OFF


class Holiday(SQLModel, table=True):
    date: str = Field(primary_key=True)  # YYYY-MM-DD
    name: str


class Patient(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    mobile: str = Field(index=True, unique=True)
    year_of_birth: Optional[int] = None


class Appointment(SQLModel, table=True):
    id: str = Field(primary_key=True)
    patient_id: str = Field(foreign_key="patient.id", index=True)
    doctor_id: str = Field(foreign_key="doctor.id", index=True)
    speciality: str
    visit_type: str  # new / follow_up
    date: str = Field(index=True)  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str  # HH:MM
    status: str = Field(default="booked", index=True)  # booked / cancelled / completed
    booked_by: str = "patient"
    cancelled_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLog(SQLModel, table=True):
    """Every booking, cancel, completion and login is recorded here."""
    id: Optional[int] = Field(default=None, primary_key=True)
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor_role: str
    actor_id: str
    action: str
    detail: str = ""
