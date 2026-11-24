import { CalendarClock, CalendarX2, History, Repeat } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, fmtDate, fmtTime } from "../api";
import { useAuth } from "../auth";
import BookingPanel from "../components/BookingPanel";
import { Alert, Empty, PageHeader, StatusBadge, useAppointmentsRefresh, useToast } from "../components/ui";

export default function PatientDashboard() {
  const { user } = useAuth();
  const toast = useToast();
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [reschedule, setReschedule] = useState(null);

  const load = useCallback(() => api.appointments().then(setItems).catch((e) => setError(e.message)), []);
  useEffect(() => { load(); }, [load]);
  useAppointmentsRefresh(load);

  const cancel = async (a) => {
    if (!window.confirm(`Cancel ${a.id} with ${a.doctor_name} on ${fmtDate(a.date)} at ${fmtTime(a.start_time)}?`)) return;
    setError("");
    try {
      await api.cancel(a.id);
      toast(`${a.id} cancelled. The slot is now free for others.`);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  const upcoming = items.filter((a) => a.status === "booked");
  const past = items.filter((a) => a.status !== "booked").reverse();

  return (
    <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <PageHeader eyebrow="Patient" title={`Hello, ${user.name.split(" ")[0]} 👋`}>
        <p className="text-sm text-slate-500">Tip: tap the mic in the corner to book by voice.</p>
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          {reschedule ? (
            <BookingPanel key={reschedule.id} rescheduleFrom={reschedule} onBooked={() => { setReschedule(null); load(); }} onCancelReschedule={() => setReschedule(null)} />
          ) : (
            <BookingPanel onBooked={load} />
          )}
        </div>

        <div className="space-y-6 lg:col-span-2">
          <Alert onClose={() => setError("")}>{error}</Alert>
          <section className="card">
            <h2 className="flex items-center gap-2 border-b border-slate-100 px-6 py-4 font-bold"><CalendarClock className="h-5 w-5 text-brand-600" /> Upcoming</h2>
            {upcoming.length === 0 ? <Empty icon={CalendarClock} title="No upcoming appointments" text="Pick a doctor and time to book your first visit." /> : (
              <ul className="divide-y divide-slate-100">
                {upcoming.map((a) => (
                  <li key={a.id} className="px-6 py-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold">{a.doctor_name}</p>
                        <p className="text-sm text-slate-500">{a.speciality} · {a.visit_type === "new" ? "New" : "Follow-up"} · <span className="font-mono text-xs">{a.id}</span></p>
                        <p className="mt-1 text-sm font-semibold text-brand-700">{fmtDate(a.date, { weekday: "long", day: "numeric", month: "short" })} · {fmtTime(a.start_time)}</p>
                      </div>
                      <StatusBadge status={a.status} />
                    </div>
                    <div className="mt-3 flex gap-2">
                      <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setReschedule(a)}><Repeat className="h-3.5 w-3.5" /> Reschedule</button>
                      <button className="btn-danger px-3 py-1.5 text-xs" onClick={() => cancel(a)}><CalendarX2 className="h-3.5 w-3.5" /> Cancel</button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <h2 className="flex items-center gap-2 border-b border-slate-100 px-6 py-4 font-bold"><History className="h-5 w-5 text-slate-400" /> History</h2>
            {past.length === 0 ? <Empty title="No past visits yet" /> : (
              <ul className="divide-y divide-slate-100 text-sm">
                {past.map((a) => (
                  <li key={a.id} className="flex items-center justify-between px-6 py-3">
                    <span>{fmtDate(a.date)} · {a.doctor_name} · {a.speciality}</span>
                    <StatusBadge status={a.status} />
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
