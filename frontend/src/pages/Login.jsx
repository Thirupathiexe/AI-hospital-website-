import { BriefcaseMedical, Stethoscope, User } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { Alert, Spinner, useToast } from "../components/ui";

const ROLES = [
  { id: "patient", label: "Patient", icon: User },
  { id: "staff", label: "Staff", icon: BriefcaseMedical },
  { id: "doctor", label: "Doctor", icon: Stethoscope },
];

export default function Login() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const [role, setRole] = useState("patient");
  const [form, setForm] = useState({ name: "", mobile: "", doctor_id: "", access_code: "" });
  const [doctors, setDoctors] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (user) nav(`/${user.role}`, { replace: true }); }, [user, nav]);
  useEffect(() => { api.doctors().then(setDoctors).catch(() => {}); }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const body = { role };
      if (role === "patient") Object.assign(body, { name: form.name, mobile: form.mobile });
      if (role === "staff") Object.assign(body, { name: form.name });
      if (role === "doctor") Object.assign(body, { doctor_id: form.doctor_id });
      if (role !== "patient" && form.access_code) body.access_code = form.access_code;
      const u = await login(body);
      if (u.newPatient) toast(`Welcome, ${u.name}! Your patient profile has been created.`);
      nav(`/${u.role}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="relative grid min-h-[calc(100vh-4rem)] place-items-center px-4 py-12">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,var(--color-brand-100),transparent_60%)]" />
      <div className="card w-full max-w-md p-8 shadow-xl shadow-slate-200/60">
        <h1 className="text-2xl font-extrabold tracking-tight">Welcome to NetraCare</h1>
        <p className="mt-1 text-sm text-slate-500">Log in to book and manage appointments.</p>

        <div className="mt-6 grid grid-cols-3 gap-1 rounded-xl bg-slate-100 p-1" role="tablist">
          {ROLES.map(({ id, label, icon: Icon }) => (
            <button key={id} role="tab" aria-selected={role === id} onClick={() => { setRole(id); setError(""); }}
              className={`flex items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-semibold transition ${role === id ? "bg-white text-brand-700 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>
              <Icon className="h-4 w-4" /> {label}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="mt-6 space-y-4">
          {role === "patient" && (
            <>
              <div>
                <label className="label" htmlFor="mobile">Mobile number</label>
                <input id="mobile" className="input" inputMode="numeric" autoComplete="tel" placeholder="10-digit mobile"
                  maxLength={10} pattern="[0-9]{10}" required value={form.mobile}
                  onChange={(e) => setForm({ ...form, mobile: e.target.value.replace(/\D/g, "") })} />
              </div>
              <div>
                <label className="label" htmlFor="name">Full name</label>
                <input id="name" className="input" autoComplete="name" placeholder="e.g. Asha Verma" required maxLength={60} value={form.name} onChange={set("name")} />
              </div>
              <p className="text-xs text-slate-500">New here? Enter your details and we'll create your profile.</p>
            </>
          )}
          {role === "staff" && (
            <div>
              <label className="label" htmlFor="sname">Your name</label>
              <input id="sname" className="input" placeholder="e.g. Front Desk" required maxLength={60} value={form.name} onChange={set("name")} />
            </div>
          )}
          {role === "doctor" && (
            <div>
              <label className="label" htmlFor="doc">Choose your name</label>
              <select id="doc" className="input" required value={form.doctor_id} onChange={set("doctor_id")}>
                <option value="">Select doctor…</option>
                {doctors.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
          )}
          {role !== "patient" && (
            <div>
              <label className="label" htmlFor="code">Access code <span className="normal-case text-slate-400">(if your clinic set one)</span></label>
              <input id="code" type="password" className="input" autoComplete="off" maxLength={64} value={form.access_code} onChange={set("access_code")} />
            </div>
          )}
          <Alert onClose={() => setError("")}>{error}</Alert>
          <button className="btn-primary w-full py-3" disabled={busy}>{busy ? <Spinner className="h-4 w-4 text-white" /> : "Continue"}</button>
        </form>
        <p className="mt-6 text-center text-xs text-slate-400">Demo login: 9000000001 · Asha Verma</p>
      </div>
    </main>
  );
}
