import { CalendarDays, CheckCircle2, ChevronLeft, ChevronRight, Clock } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { addDays, api, fmtDate, fmtTime } from "../api";
import { Alert, Spinner, useToast } from "./ui";

/** Step-by-step booking: speciality -> doctor -> date -> time -> confirm.
 *  The screen only helps; the backend checks every rule again when you press Book. */
export default function BookingPanel({ patient, onBooked, rescheduleFrom, onCancelReschedule }) {
  const toast = useToast();
  const [doctors, setDoctors] = useState([]);
  const [today, setToday] = useState(null);
  const [speciality, setSpeciality] = useState(rescheduleFrom?.speciality || "");
  const [doctorId, setDoctorId] = useState(rescheduleFrom?.doctor_id || "");
  const [visitType, setVisitType] = useState(rescheduleFrom?.visit_type || "new");
  const [date, setDate] = useState("");
  const [weekStart, setWeekStart] = useState("");
  const [slots, setSlots] = useState(null);
  const [time, setTime] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([api.doctors(), api.clock()]).then(([d, c]) => {
      setDoctors(d);
      setToday(c.today);
      setDate(c.today);
      setWeekStart(c.today);
    }).catch((e) => setError(e.message));
  }, []);

  const specialities = useMemo(() => [...new Set(doctors.flatMap((d) => d.specialities))].sort(), [doctors]);
  const matching = doctors.filter((d) => !speciality || d.specialities.includes(speciality));
  const doctor = doctors.find((d) => d.id === doctorId);

  const loadSlots = useCallback(() => {
    if (!doctorId || !date) return;
    setSlots(null);
    setTime("");
    api.slots({ doctor_id: doctorId, date, visit_type: visitType, speciality: speciality || doctor?.specialities[0] })
      .then(setSlots).catch((e) => setError(e.message));
  }, [doctorId, date, visitType, speciality, doctor]);
  useEffect(loadSlots, [loadSlots]);

  const days = today ? [...Array(7)].map((_, i) => addDays(weekStart, i)) : [];
  const maxDay = today ? addDays(today, 30) : "";

  const book = async () => {
    setError("");
    setBusy(true);
    const body = { doctor_id: doctorId, speciality: speciality || doctor.specialities[0], visit_type: visitType, date, start_time: time };
    try {
      const appt = rescheduleFrom
        ? await api.reschedule(rescheduleFrom.id, body)
        : await api.book(patient ? { ...body, patient_id: patient.id } : body);
      toast(`Booked ${appt.id}: ${appt.doctor_name}, ${fmtDate(appt.date)} at ${fmtTime(appt.start_time)}`);
      window.dispatchEvent(new Event("netracare:changed"));
      setTime("");
      loadSlots();
      onBooked?.(appt);
    } catch (e) {
      setError(e.message);
      loadSlots();
    } finally {
      setBusy(false);
    }
  };

  const am = slots?.slots.filter((t) => t < "13:00") || [];
  const pm = slots?.slots.filter((t) => t >= "14:00") || [];

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">{rescheduleFrom ? `Reschedule ${rescheduleFrom.id}` : patient ? `Book for ${patient.name}` : "Book an appointment"}</h2>
        {rescheduleFrom && <button className="text-sm font-semibold text-slate-500 hover:text-slate-800" onClick={onCancelReschedule}>Cancel</button>}
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        <div>
          <label className="label">Speciality</label>
          <select className="input" value={speciality} onChange={(e) => { setSpeciality(e.target.value); setDoctorId(""); }}>
            <option value="">Any</option>
            {specialities.map((s) => <option key={s}>{s}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Doctor</label>
          <select className="input" value={doctorId} onChange={(e) => setDoctorId(e.target.value)}>
            <option value="">Choose doctor…</option>
            {matching.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Visit type</label>
          <div className="grid grid-cols-2 gap-1 rounded-xl bg-slate-100 p-1">
            {[["new", "New · 20m"], ["follow_up", "Follow-up · 10m"]].map(([v, l]) => (
              <button key={v} onClick={() => setVisitType(v)} className={`rounded-lg py-2 text-xs font-semibold ${visitType === v ? "bg-white text-brand-700 shadow-sm" : "text-slate-500"}`}>{l}</button>
            ))}
          </div>
        </div>
      </div>

      {doctor && (
        <>
          <div className="mt-6 flex items-center justify-between">
            <label className="label mb-0 flex items-center gap-1.5"><CalendarDays className="h-4 w-4" /> Date</label>
            <div className="flex gap-1">
              <button className="btn-ghost px-2 py-1" disabled={weekStart <= today} onClick={() => setWeekStart(addDays(weekStart, -7))} aria-label="Previous week"><ChevronLeft className="h-4 w-4" /></button>
              <button className="btn-ghost px-2 py-1" disabled={addDays(weekStart, 7) > maxDay} onClick={() => setWeekStart(addDays(weekStart, 7))} aria-label="Next week"><ChevronRight className="h-4 w-4" /></button>
            </div>
          </div>
          <div className="mt-2 grid grid-cols-7 gap-1.5">
            {days.map((d) => {
              const disabled = d > maxDay;
              const [wd, num] = [fmtDate(d, { weekday: "short" }), fmtDate(d, { day: "numeric" })];
              return (
                <button key={d} disabled={disabled} onClick={() => setDate(d)}
                  className={`flex flex-col items-center rounded-xl py-2 text-xs transition disabled:opacity-30 ${date === d ? "bg-brand-600 text-white shadow-lg shadow-brand-600/30" : "bg-slate-50 ring-1 ring-slate-200 hover:bg-brand-50"}`}>
                  <span className="font-medium opacity-80">{wd}</span>
                  <span className="text-base font-bold">{num}</span>
                </button>
              );
            })}
          </div>

          <div className="mt-6">
            <label className="label flex items-center gap-1.5"><Clock className="h-4 w-4" /> Free times — {fmtDate(date, { weekday: "long", day: "numeric", month: "long" })}</label>
            {!slots ? <Spinner /> : slots.slots.length === 0 ? (
              <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800 ring-1 ring-amber-200">{slots.reason}</p>
            ) : (
              <div className="space-y-3">
                {[["Morning", am], ["Afternoon", pm]].map(([label, list]) => list.length > 0 && (
                  <div key={label}>
                    <p className="mb-1.5 text-xs font-medium text-slate-400">{label}</p>
                    <div className="grid grid-cols-4 gap-1.5 sm:grid-cols-6 lg:grid-cols-8">
                      {list.map((t) => (
                        <button key={t} onClick={() => setTime(t)}
                          className={`rounded-lg py-2 text-xs font-semibold transition ${time === t ? "bg-brand-600 text-white" : "bg-white ring-1 ring-slate-200 hover:ring-brand-400"}`}>{fmtTime(t)}</button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      <div className="mt-6 space-y-3">
        <Alert onClose={() => setError("")}>{error}</Alert>
        {time && (
          <div className="flex flex-col gap-3 rounded-xl bg-brand-50 p-4 ring-1 ring-brand-100 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm"><CheckCircle2 className="mr-1 inline h-4 w-4 text-brand-600" />
              <b>{doctor?.name}</b> · {speciality || doctor?.specialities[0]} · {visitType === "new" ? "New consultation" : "Follow-up"} · {fmtDate(date)} at <b>{fmtTime(time)}</b></p>
            <button className="btn-primary" disabled={busy} onClick={book}>{busy ? <Spinner className="h-4 w-4 text-white" /> : rescheduleFrom ? "Confirm reschedule" : "Confirm booking"}</button>
          </div>
        )}
      </div>
    </div>
  );
}
