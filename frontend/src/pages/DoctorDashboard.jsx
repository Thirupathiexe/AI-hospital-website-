import { CheckCheck, Stethoscope } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { addDays, api, fmtDate, fmtTime } from "../api";
import { useAuth } from "../auth";
import { Alert, Empty, PageHeader, StatusBadge, useToast } from "../components/ui";

export default function DoctorDashboard() {
  const { user } = useAuth();
  const toast = useToast();
  const [date, setDate] = useState("");
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => { api.clock().then((c) => setDate(c.today)); }, []);
  const load = useCallback(() => {
    if (date) api.appointments({ date }).then(setItems).catch((e) => setError(e.message));
  }, [date]);
  useEffect(() => { load(); }, [load]);

  const complete = async (a) => {
    try {
      await api.complete(a.id);
      toast(`Visit ${a.id} with ${a.patient_name} marked completed.`);
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  const active = items.filter((a) => a.status !== "cancelled");

  return (
    <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <PageHeader eyebrow="Doctor" title={user.name}>
        <div className="flex gap-1">
          <button className="btn-ghost px-3" onClick={() => setDate(addDays(date, -1))} aria-label="Previous day">‹</button>
          <input type="date" className="input" value={date} onChange={(e) => setDate(e.target.value)} />
          <button className="btn-ghost px-3" onClick={() => setDate(addDays(date, 1))} aria-label="Next day">›</button>
        </div>
      </PageHeader>
      <div className="mb-4"><Alert onClose={() => setError("")}>{error}</Alert></div>
      <section className="card">
        <h2 className="border-b border-slate-100 px-6 py-4 font-bold">{date && fmtDate(date, { weekday: "long", day: "numeric", month: "long" })} · {active.length} patients</h2>
        {active.length === 0 ? <Empty icon={Stethoscope} title="No patients booked" text="Your schedule for this day is clear." /> : (
          <ul className="divide-y divide-slate-100">
            {active.map((a) => (
              <li key={a.id} className="flex flex-col gap-3 px-6 py-4 sm:flex-row sm:items-center">
                <div className="w-32 shrink-0 font-bold text-brand-700">{fmtTime(a.start_time)}<span className="block text-xs font-medium text-slate-400">until {fmtTime(a.end_time)}</span></div>
                <div className="flex-1">
                  <p className="font-semibold">{a.patient_name} <span className="font-mono text-xs text-slate-400">{a.patient_id}</span></p>
                  <p className="text-sm text-slate-500">{a.speciality} · {a.visit_type === "new" ? "New consultation" : "Follow-up"} · {a.id}</p>
                </div>
                <StatusBadge status={a.status} />
                {a.status === "booked" && <button className="btn-primary px-3 py-1.5 text-xs" onClick={() => complete(a)}><CheckCheck className="h-4 w-4" /> Mark completed</button>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
