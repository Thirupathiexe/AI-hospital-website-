# NetraCare: Eye Clinic Booking Website with an AI Voice Assistant

Patients, staff and doctors log in and manage eye-clinic appointments. A FastAPI backend refuses any
booking that breaks a clinic rule. **Netra**, the voice assistant, books by voice using the same rules.
NetraCare is fictional and all data is synthetic.

```
netracare/
├── backend/                FastAPI + SQLModel + SQLite
│   ├── app/
│   │   ├── config.py       settings from env, the one clinic clock
│   │   ├── models.py       tables: doctor, weekly schedule, holiday, patient, appointment, audit log
│   │   ├── db.py           engine and CSV loader (R1)
│   │   ├── rules.py        ★ every clinic rule, in one place (R2, R4, R5)
│   │   ├── services.py     role-scoped reads (who can see what)
│   │   ├── security.py     signed tokens, role checks, rate limits, security headers
│   │   ├── schemas.py      strict Pydantic input validation
│   │   ├── main.py         API routes, error handling, serves the built website
│   │   └── assistant/      Part 4: AI voice assistant
│   │       ├── agent.py    Claude tool loop, conversation memory
│   │       ├── tools.py    tools that call rules.py as the logged-in user
│   │       ├── safety.py   red-flag check that runs before any AI
│   │       └── fallback.py basic assistant that works with no API key
│   ├── data/               the data pack CSVs
│   └── tests/              52 automated tests (all 38 rule_tests.csv cases)
└── frontend/               React 19 + Vite + Tailwind CSS v4 + lucide icons
    └── src/
        ├── pages/          Landing, Login, Patient, Staff, Doctor
        └── components/     BookingPanel, VoiceAssistant, Navbar, ui
```

---

## Run it

You need Python 3.11+ and Node 20+.

**1. Backend**
```bash
cd netracare/backend
pip install -r requirements.txt
copy .env.example .env        # macOS/Linux: cp .env.example .env
```
Put a long random `SECRET_KEY` in `.env`. Add `ANTHROPIC_API_KEY` for AI mode; without it the assistant runs in basic mode.

**2. Frontend: build it once**
```bash
cd netracare/frontend
npm install
npm run build
```

**3. Start everything** (FastAPI serves the API and the built website together)
```bash
cd netracare/backend
python -m uvicorn app.main:app --port 8000
```
Open http://localhost:8000. API docs are at http://localhost:8000/api/docs.

**While developing the frontend**, run `npm run dev` in `frontend/` as well and open http://localhost:5173. Its `/api` calls are proxied to port 8000.

**Run the tests**
```bash
cd netracare/backend
python -m pytest -q
```

**Demo logins**
- Patient: mobile `9000000001`, name `Asha Verma` (any new mobile number creates a new patient)
- Doctor: pick a name from the list
- Staff: any name

---

## The project in 4 parts

### Part 1: Foundation (data, database, loader). Requirement R1
1. Read the handout and the data pack README. List the tables: doctors, weekly_schedule, holidays, patients, appointments.
2. `models.py` defines them with SQLModel. Dates are stored as `YYYY-MM-DD` and times as `HH:MM`, the same as the CSVs.
3. `db.py` loads the CSVs on startup. Appointments start empty.
4. `config.now()` is the only clock in the app. Set `CLINIC_NOW=2026-11-02 10:00` and every rule uses that fixed time, which is how the tests get answers that never change.

**Check:** log in as Asha Verma (9000000001) and you see all 5 doctors.

### Part 2: Rules engine and secure API. R2 to R5
1. **Every rule lives in `rules.py`.** `check_booking()` runs the checks in a fixed order and raises `RuleError(code, message)` at the first one that fails. The codes match the data pack README: `INVALID_START_TIME`, `IN_PAST`, `BEYOND_30_DAYS`, `CLINIC_CLOSED`, `HOLIDAY`, `OUTSIDE_SESSION`, `ENDS_AFTER_SESSION`, `DOCTOR_OFF`, `SURGERY_SESSION`, `SPECIALITY_MISMATCH`, `DOUBLE_BOOKED`, `ACTIVE_BOOKING_EXISTS`, `NO_PREVIOUS_VISIT`, `FOLLOW_UP_DIFFERENT_DOCTOR`.
2. `book`, `cancel`, `reschedule` and `complete` all go through those checks. A lock wraps each check-and-write, so two people can never book the same slot at the same moment.
3. `free_slots()` uses the same checks, so the slots on screen always match what the backend will accept.
4. Cancelling: a patient can cancel up to 2 hours before. Inside that, the reply is `INSIDE_2_HOURS` ("Please contact Staff"). Staff can always cancel.
5. Rescheduling (stretch goal) is a cancel plus a new booking in one step. If the new booking is refused, the original stays.
6. Try every endpoint at `/api/docs` before building any screens.

**Request flow, from clicking "Book" to a database row:**
`BookingPanel.jsx` → `POST /api/appointments` → Pydantic checks the input shape → `current_actor()` checks the signed cookie → `require("patient","staff")` checks the role → `rules.book()` runs every rule → a row is written in `appointment` plus one in `audit_log` → JSON comes back. A refusal returns `{"code","message"}` and the screen shows the message.

### Part 3: Frontend (R6)
- **Stack:** React + Vite + Tailwind CSS v4 + lucide-react icons. All free and open source.
- **Landing page:** hero, live "next available" card, services, doctor cards, a weekly OPD grid built from the real schedule, a voice-booking section and a call to action.
- **Patient:** a step-by-step booking panel (speciality → doctor → 7-day picker → morning and afternoon slots → confirm), upcoming visits with reschedule and cancel, and visit history.
- **Staff:** appointments by day and doctor (with patient mobile numbers), cancel any appointment, find a patient or register a walk-in, then book for them.
- **Doctor:** their own day schedule, with "Mark completed".
- Refusals are shown in plain words, for example *"Dr. Meera Iyer is not at the clinic on Thursdays."*

### Part 4: AI voice assistant
- **Voice in and out:** the browser's free Web Speech API. `SpeechRecognition` listens (Chrome or Edge) and `speechSynthesis` reads replies aloud. You can choose English, Hindi or Tamil, or type instead.
- **AI mode** (when `ANTHROPIC_API_KEY` is set): Claude (`claude-opus-5-5`, low effort for fast voice replies) gets six tools: `list_doctors`, `get_free_slots`, `list_appointments`, `book_appointment`, `cancel_appointment` and `find_patient` (staff only). **Each tool calls `rules.py` as the logged-in user.** The AI can never do more than that user could do by hand, and a patient's AI can't act for another patient.
- **Confirmation:** booking and cancel tools need `user_confirmed=true`. The assistant reads the details back and waits for a "yes".
- **Safety:** `safety.py` checks for red flags (sudden vision loss, chemical splash, injury, flashes with a curtain over vision) with fixed patterns **before** any AI call, and sends the person to emergency care.
- **Basic mode** (no key, or the AI can't be reached): `fallback.py` understands requests like *"free slots with Dr Shah on Friday"* or *"book Dr Rao tomorrow at 10 AM for cataract"*, and asks for confirmation before booking.
- Server-side fallbacks are switched on (`fallbacks="default"`): if Claude declines a request, the API retries it on a fallback model automatically.

---

## Security

| Threat | Protection |
|---|---|
| Patient reads or changes someone else's data | Every query is filtered by the logged-in user in the backend (`services.py`, `rules.py`). A patient's `patient_id` comes from the token, never from the request body. Tested in `test_api_security.py`. |
| Forged or edited login | Tokens are HMAC-SHA256 signed with `SECRET_KEY`, checked with `compare_digest`, and expire after 8 hours. |
| Token theft through XSS | The website keeps the token in an **HttpOnly, SameSite=Strict** cookie that JavaScript can't read. React escapes all output, and a strict Content-Security-Policy allows scripts only from this site. |
| CSRF | SameSite=Strict cookie, an Origin check, and JSON-only POSTs. |
| SQL injection | Only ORM queries with bound parameters. No string-built SQL. |
| Bad or oversized input | Strict Pydantic schemas (regex patterns, `extra="forbid"`) and a 16 KB body limit. |
| Brute force or spam | Per-IP rate limits: login 10/min, assistant 20/min, other calls 120/min. |
| Clickjacking and sniffing | `X-Frame-Options: DENY`, `frame-ancestors 'none'`, `nosniff`, `no-referrer`. |
| Prompt injection on the AI | Tools run with the user's own permissions, booking needs confirmation, conversations are tied to their owner, and history is kept on the server (clients can't inject fake tool results). |
| Leaking internals | One generic 500 handler. Refusals return only a code and a message. |
| Audit | Every login, booking, cancel and completion is written to `audit_log`. |

> These logins follow the brief's no-password design and are fine for a classroom. Before real use, add real
> authentication (OTP to the mobile number), serve over HTTPS with `COOKIE_SECURE=true`, set
> `STAFF_ACCESS_CODE` and `DOCTOR_ACCESS_CODE`, and move rate limits and conversations to Redis.

---

## "Done when" checks (handout section 09)

All of these pass against the live server (see `tests/` for the automated versions):

| Try this | Result |
|---|---|
| New consultation with a free doctor | Booked, 20 minutes |
| Same doctor and time, another patient | `DOUBLE_BOOKED` |
| Dr. Rao on a Thursday morning | `SURGERY_SESSION` |
| Dr. Iyer on a Thursday | `DOCTOR_OFF` |
| 1:30 PM / Sunday / holiday | `OUTSIDE_SESSION` / `CLINIC_CLOSED` / `HOLIDAY` |
| New consultation at 12:50 PM | `ENDS_AFTER_SESSION` |
| More than 30 days ahead / in the past | `BEYOND_30_DAYS` / `IN_PAST` |
| Dr. Khan for Glaucoma | `SPECIALITY_MISMATCH` |
| Second Cataract booking | `ACTIVE_BOOKING_EXISTS` |
| Follow-up never seen / different doctor | `NO_PREVIOUS_VISIT` / `FOLLOW_UP_DIFFERENT_DOCTOR` |
| Patient cancels inside 2 hours | `INSIDE_2_HOURS`: "Please contact Staff" |
| Staff cancels the same appointment | Cancelled |
| Cancel, then rebook as someone else | Booked |

## Demo video (3 minutes or less)
1. Log in as Asha → book Dr. Shah (Retina) → it appears under Upcoming.
2. Try Dr. Iyer on a Thursday → plain-words refusal.
3. Tap the mic: "Book Dr Rao on Friday at 11 AM for cataract" → "yes" → booked.
4. Log in as Staff → cancel an appointment that starts within 2 hours.
