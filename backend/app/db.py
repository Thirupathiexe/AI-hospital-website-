"""Database engine, session helper and the CSV loader (R1)."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from . import config
from .models import Appointment, Doctor, Holiday, Patient, WeeklySchedule

engine = create_engine(config.DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.close()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def _rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_data_pack(session: Session, data_dir: Path | None = None, with_seed: bool = False) -> None:
    """Load the CSVs. Safe to run again: rows that already exist are left alone.
    Appointments start empty unless with_seed=True (used by the automated tests)."""
    data_dir = data_dir or config.DATA_DIR

    for r in _rows(data_dir / "doctors.csv"):
        if not session.get(Doctor, r["doctor_id"]):
            session.add(Doctor(id=r["doctor_id"], name=r["name"], specialities=r["specialities"]))
    session.commit()

    if not session.exec(select(WeeklySchedule)).first():
        for r in _rows(data_dir / "weekly_schedule.csv"):
            session.add(WeeklySchedule(doctor_id=r["doctor_id"], day=r["day"], session=r["session"], status=r["status"].upper()))
    for r in _rows(data_dir / "holidays.csv"):
        if not session.get(Holiday, r["date"]):
            session.add(Holiday(date=r["date"], name=r["name"]))
    for r in _rows(data_dir / "patients.csv"):
        if not session.get(Patient, r["patient_id"]):
            session.add(Patient(id=r["patient_id"], name=r["name"], mobile=r["mobile"],
                                year_of_birth=int(r["year_of_birth"]) if r.get("year_of_birth") else None))
    session.commit()

    if with_seed:
        for r in _rows(data_dir / "stretch" / "appointments_seed.csv"):
            if not session.get(Appointment, r["appointment_id"]):
                session.add(Appointment(id=r["appointment_id"], patient_id=r["patient_id"], doctor_id=r["doctor_id"],
                                        speciality=r["speciality"], visit_type=r["visit_type"], date=r["date"],
                                        start_time=r["start_time"], end_time=r["end_time"], status=r["status"],
                                        booked_by="seed"))
        session.commit()


def init_db(with_seed: bool = False) -> None:
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        load_data_pack(session, with_seed=with_seed)


if __name__ == "__main__":  # python -m app.db
    init_db()
    print("Database ready at", config.DATABASE_URL)
