import { CalendarX2, Search, UserPlus, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { addDays, api, fmtDate, fmtTime } from "../api";
import BookingPanel from "../components/BookingPanel";
import { Alert, Empty, PageHeader, StatusBadge, useAppointmentsRefresh, useToast } from "../components/ui";

export default function StaffDashboard() {
  const toast = useToast();
  const [tab, setTab] = useState("schedule");
  const [date, setDate] = useState("");
  const [doctorId, setDoctorId] = useState("");
  const [doctors, setDoctors] = useState([]);
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.doctors(), api.clock()]).then(([d, c]) => { setDoctors(d); setDate(c.today); });
  }, []);

  const load = useCallback(() => {
    if (!date) return;
    api.appointments({ date, doctor_id: doctorId }).then(setItems).catch((e) => setError(e.message));
  }, [date, doctorId]);
  useEffect(() => { load(); }, [load]);
  useAppointmentsRefresh(load);

  const cancel = async (a) => {
    if (!window.confirm(`Cancel ${a.id} for ${a.patient_name}?`)) return;
    try {
      await api.cancel(a.id);
      toast(`${a.id} cancelled.`);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  const booked = items.filter((a) => a.status === "booked").length;

  return (
    <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <PageHeader eyebrow="Staff desk" title="Clinic appointments">
        <div className="grid grid-cols-2 gap-1 rounded-xl bg-slate-100 p-1">
          {[["schedule", "Schedule"], ["book", "Book for patient"]].map(([id, l]) => (
            <button key={id} onClick={() => setTab(id)} className={`rounded-lg px-4 py-2 text-sm font-semibold ${tab === id ? "bg-white text-brand-700 shadow-sm" : "text-slate-500"}`}>{l}</button>
          ))}
        </div>
      </PageHeader>
      <div className="mb-4"><Alert onClose={() => setError("")}>{error}</Alert></div>

      {tab === "schedule" ? (
        <section className="card">
          <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-end">
            <div>
              <label className="label">Date</label>
              <div className="flex gap-1">
                <button className="btn-ghost px-3" onClick={() => setDate(addDays(date, -1))} aria-label="Previous day">‹</button>
                <input type="date" className="input" value={date} onChange={(e) => setDate(e.target.value)} />
                <button className="btn-ghost px-3" onClick={() => setDate(addDays(date, 1))} aria-label="Next day">›</button>
              </div>
            </div>
            <div className="sm:w-64">
              <label className="label">Doctor</label>
              <select className="input" value={doctorId} onChange={(e) => setDoctorId(e.target.value)}>
                <option value="">All doctors</option>
                {doctors.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            <p className="text-sm text-slate-500 sm:ml-auto">{booked} booked · {items.length} total</p>
          </div>
          {items.length === 0 ? <Empty icon={Users} title="No appointments" text={`Nothing on ${date ? fmtDate(date) : "this day"}.`} /> : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
                  <tr>{["Time", "Doctor", "Patient", "Mobile", "Speciality", "Type", "Status", ""].map((h) => <th key={h} className="px-4 py-3 font-semibold">{h}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {items.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50/60">
                      <td className="whitespace-nowrap px-4 py-3 font-semibold">{fmtTime(a.start_time)}–{fmtTime(a.end_time)}</td>
                      <td className="px-4 py-3">{a.doctor_name}</td>
                      <td className="px-4 py-3">{a.patient_name} <span className="font-mono text-xs text-slate-400">{a.patient_id}</span></td>
                      <td className="px-4 py-3 font-mono text-xs">{a.patient_mobile}</td>
                      <td className="px-4 py-3">{a.speciality}</td>
                      <td className="px-4 py-3">{a.visit_type === "new" ? "New" : "Follow-up"}</td>
                      <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                      <td className="px-4 py-3 text-right">{a.status === "booked" && <button className="btn-danger px-3 py-1.5 text-xs" onClick={() => cancel(a)}><CalendarX2 className="h-3.5 w-3.5" /> Cancel</button>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : (
        <StaffBooking onBooked={(a) => { setDate(a.date); setTab("schedule"); }} />
      )}
    </main>
  );
}

function StaffBooking({ onBooked }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [patient, setPatient] = useState(null);
  const [walkIn, setWalkIn] = useState({ name: "", mobile: "" });
  const [error, setError] = useState("");

  useEffect(() => {
    const t = setTimeout(() => api.patients(q).then(setResults).catch(() => {}), 250);
    return () => clearTimeout(t);
  }, [q]);

  const addWalkIn = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const p = await api.addPatient(walkIn);
      setPatient(p);
      setWalkIn({ name: "", mobile: "" });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="space-y-6 lg:col-span-2">
        <section className="card p-6">
          <h2 className="flex items-center gap-2 font-bold"><Search className="h-5 w-5 text-brand-600" /> Find patient</h2>
          <input className="input mt-4" placeholder="Name, mobile or ID" value={q} onChange={(e) => setQ(e.target.value)} />
          <ul className="mt-3 max-h-72 divide-y divide-slate-100 overflow-y-auto">
            {results.map((p) => (
              <li key={p.id}>
                <button onClick={() => setPatient(p)} className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm hover:bg-brand-50 ${patient?.id === p.id ? "bg-brand-50 font-semibold" : ""}`}>
                  <span>{p.name}</span><span className="font-mono text-xs text-slate-400">{p.mobile}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
        <section className="card p-6">
          <h2 className="flex items-center gap-2 font-bold"><UserPlus className="h-5 w-5 text-brand-600" /> Walk-in patient</h2>
          <form onSubmit={addWalkIn} className="mt-4 space-y-3">
            <input className="input" placeholder="Full name" required maxLength={60} value={walkIn.name} onChange={(e) => setWalkIn({ ...walkIn, name: e.target.value })} />
            <input className="input" placeholder="10-digit mobile" required inputMode="numeric" maxLength={10} pattern="[0-9]{10}" value={walkIn.mobile} onChange={(e) => setWalkIn({ ...walkIn, mobile: e.target.value.replace(/\D/g, "") })} />
            <Alert onClose={() => setError("")}>{error}</Alert>
            <button className="btn-primary w-full">Register & select</button>
          </form>
        </section>
      </div>
      <div className="lg:col-span-3">
        {patient ? <BookingPanel key={patient.id} patient={patient} onBooked={onBooked} /> : (
          <div className="card"><Empty icon={Users} title="Choose a patient first" text="Search for an existing patient or register a walk-in." /></div>
        )}
      </div>
    </div>
  );
}
