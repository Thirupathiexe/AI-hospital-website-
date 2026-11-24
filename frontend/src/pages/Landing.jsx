import {
  ArrowRight, Baby, CalendarCheck, Clock, Droplets, Eye, Glasses, HeartPulse, Mic, ScanEye, ShieldCheck,
  Sparkles, Star, Stethoscope, Sun,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Logo } from "../components/ui";

const SERVICES = [
  { icon: ScanEye, name: "Cataract", text: "Assessment, surgery planning and follow-up care." },
  { icon: Eye, name: "Glaucoma", text: "Pressure checks and long-term monitoring." },
  { icon: HeartPulse, name: "Retina", text: "Diabetic eye checks and retinal care." },
  { icon: Sun, name: "Cornea", text: "Infections, injuries and corneal disease." },
  { icon: Glasses, name: "Refractive", text: "Glasses, contact lenses and LASIK advice." },
  { icon: Droplets, name: "Dry eye", text: "Relief for itchy, gritty and tired eyes." },
  { icon: Baby, name: "Paediatric & Squint", text: "Gentle eye care for children." },
  { icon: Stethoscope, name: "General", text: "Routine eye check-ups for the whole family." },
];

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const CELL = {
  OPD: "bg-brand-100 text-brand-800",
  SURGERY: "bg-amber-100 text-amber-800",
  OFF: "bg-slate-100 text-slate-400",
};
const GRADIENTS = ["from-brand-400 to-brand-700", "from-sky-400 to-indigo-600", "from-violet-400 to-fuchsia-600", "from-amber-400 to-orange-600", "from-emerald-400 to-teal-700"];

export default function Landing() {
  const [doctors, setDoctors] = useState([]);
  useEffect(() => { api.doctors().then(setDoctors).catch(() => {}); }, []);

  return (
    <main>
      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top_right,var(--color-brand-100),transparent_55%),radial-gradient(ellipse_at_bottom_left,#e0e7ff,transparent_50%)]" />
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:py-24">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-semibold text-brand-700 shadow-sm ring-1 ring-brand-100">
              <Sparkles className="h-3.5 w-3.5" /> Now with AI voice booking
            </span>
            <h1 className="mt-6 text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-6xl">
              See the world <span className="bg-gradient-to-r from-brand-500 to-indigo-500 bg-clip-text text-transparent">clearly</span> again.
            </h1>
            <p className="mt-6 max-w-xl text-lg text-slate-600">
              Expert eye care from five specialists. See who's free, pick a time that suits you, and book in seconds —
              or just <b>ask Netra</b>, our voice assistant.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/login" className="btn-primary px-6 py-3 text-base">Book an appointment <ArrowRight className="h-4 w-4" /></Link>
              <a href="#voice" className="btn-ghost px-6 py-3 text-base"><Mic className="h-4 w-4" /> Try voice booking</a>
            </div>
            <div className="mt-10 flex items-center gap-6 text-sm text-slate-500">
              <div className="flex -space-x-2">
                {GRADIENTS.map((g, i) => <span key={i} className={`h-9 w-9 rounded-full bg-gradient-to-br ${g} ring-2 ring-white`} />)}
              </div>
              <div>
                <div className="flex text-amber-400">{[...Array(5)].map((_, i) => <Star key={i} className="h-4 w-4 fill-current" />)}</div>
                Trusted by families across the city
              </div>
            </div>
          </div>

          {/* Hero visual */}
          <div className="relative mx-auto w-full max-w-md">
            <div className="absolute -inset-6 -z-10 rounded-[2.5rem] bg-gradient-to-br from-brand-200/60 to-indigo-200/60 blur-2xl" />
            <div className="card animate-float p-6">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-500">Next available</p>
                <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">● Live</span>
              </div>
              <div className="mt-4 flex items-center gap-4">
                <div className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-brand-400 to-brand-700 text-xl font-bold text-white">AR</div>
                <div>
                  <p className="font-bold">Dr. Anand Rao</p>
                  <p className="text-sm text-slate-500">Cataract · General</p>
                </div>
              </div>
              <div className="mt-5 grid grid-cols-4 gap-2">
                {["9:00", "9:20", "10:10", "11:30", "2:00", "2:40", "3:30", "4:50"].map((t, i) => (
                  <span key={t} className={`rounded-lg py-2 text-center text-sm font-semibold ${i === 2 ? "bg-brand-600 text-white" : "bg-slate-50 text-slate-700 ring-1 ring-slate-200"}`}>{t}</span>
                ))}
              </div>
              <div className="mt-5 flex items-center gap-3 rounded-xl bg-slate-900 p-3 text-sm text-white">
                <span className="relative grid h-9 w-9 place-items-center rounded-full bg-brand-500">
                  <span className="absolute inset-0 animate-pulse-ring rounded-full bg-brand-400" />
                  <Mic className="relative h-4 w-4" />
                </span>
                <span>"Book Dr. Rao tomorrow at 10:10 for cataract"</span>
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="mx-auto max-w-7xl px-4 pb-16 sm:px-6">
          <div className="glass grid grid-cols-2 gap-6 rounded-2xl p-6 shadow-sm md:grid-cols-4">
            {[["5", "Eye specialists"], ["9", "Specialities"], ["6 days", "Open every week"], ["24×7", "Online & voice booking"]].map(([n, l]) => (
              <div key={l} className="text-center">
                <p className="text-3xl font-extrabold text-brand-700">{n}</p>
                <p className="text-sm text-slate-500">{l}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SERVICES */}
      <section id="services" className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-600">What we treat</p>
          <h2 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">Complete care for your eyes</h2>
        </div>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {SERVICES.map(({ icon: Icon, name, text }) => (
            <div key={name} className="card group p-6 transition hover:-translate-y-1 hover:shadow-xl hover:shadow-brand-600/10">
              <span className="grid h-12 w-12 place-items-center rounded-xl bg-brand-50 text-brand-600 transition group-hover:bg-brand-600 group-hover:text-white"><Icon className="h-6 w-6" /></span>
              <h3 className="mt-4 font-bold">{name}</h3>
              <p className="mt-1 text-sm text-slate-500">{text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* DOCTORS */}
      <section id="doctors" className="bg-white py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-600">Our team</p>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">Meet our specialists</h2>
          </div>
          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-5">
            {doctors.map((d, i) => (
              <div key={d.id} className="card overflow-hidden text-center">
                <div className={`h-24 bg-gradient-to-br ${GRADIENTS[i % 5]}`} />
                <div className="-mt-10 px-5 pb-6">
                  <div className="mx-auto grid h-20 w-20 place-items-center rounded-full bg-white text-2xl font-extrabold text-slate-700 shadow-lg ring-4 ring-white">
                    {d.name.replace("Dr. ", "").split(" ").map((p) => p[0]).join("")}
                  </div>
                  <p className="mt-3 font-bold">{d.name}</p>
                  <div className="mt-2 flex flex-wrap justify-center gap-1">
                    {d.specialities.map((s) => <span key={s} className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">{s}</span>)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TIMINGS */}
      <section id="timings" className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <div className="grid gap-10 lg:grid-cols-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-600">Weekly OPD</p>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight">Who's in, and when</h2>
            <p className="mt-4 text-slate-600">OPD runs <b>9 AM – 1 PM</b> and <b>2 PM – 6 PM</b>, Monday to Saturday. Closed on Sundays and clinic holidays.</p>
            <ul className="mt-6 space-y-3 text-sm text-slate-600">
              <li className="flex gap-3"><Clock className="h-5 w-5 text-brand-600" /> New consultation: 20 minutes</li>
              <li className="flex gap-3"><CalendarCheck className="h-5 w-5 text-brand-600" /> Follow-up: 10 minutes, with the same doctor</li>
              <li className="flex gap-3"><ShieldCheck className="h-5 w-5 text-brand-600" /> Book up to 30 days ahead, cancel up to 2 hours before</li>
            </ul>
            <div className="mt-6 flex gap-4 text-xs font-medium">
              <span className="flex items-center gap-1.5"><i className="h-3 w-3 rounded bg-brand-200" /> OPD</span>
              <span className="flex items-center gap-1.5"><i className="h-3 w-3 rounded bg-amber-200" /> Surgery</span>
              <span className="flex items-center gap-1.5"><i className="h-3 w-3 rounded bg-slate-200" /> Off</span>
            </div>
          </div>
          <div className="card overflow-x-auto lg:col-span-2">
            <table className="w-full min-w-[620px] text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wide text-slate-400">
                  <th className="p-4 text-left font-semibold">Doctor</th>
                  {DAYS.map((d) => <th key={d} className="p-2 font-semibold">{d}</th>)}
                </tr>
              </thead>
              <tbody>
                {doctors.map((d) => (
                  <tr key={d.id} className="border-t border-slate-100">
                    <td className="whitespace-nowrap p-4 font-semibold">{d.name}</td>
                    {DAYS.map((day) => (
                      <td key={day} className="p-1.5">
                        <div className="grid grid-cols-2 gap-1">
                          {["AM", "PM"].map((s) => {
                            const st = d.schedule[`${day}-${s}`] || "OFF";
                            return <span key={s} title={`${day} ${s}: ${st}`} className={`rounded-md py-1.5 text-center text-[10px] font-bold ${CELL[st]}`}>{s}</span>;
                          })}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* VOICE */}
      <section id="voice" className="px-4 pb-20 sm:px-6">
        <div className="mx-auto max-w-7xl overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 via-brand-900 to-slate-900 p-8 text-white sm:p-14">
          <div className="grid items-center gap-10 lg:grid-cols-2">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold"><Mic className="h-3.5 w-3.5" /> Netra voice assistant</span>
              <h2 className="mt-4 text-3xl font-extrabold tracking-tight sm:text-4xl">Just say it. We'll book it.</h2>
              <p className="mt-4 text-white/70">Tap the mic and speak naturally. Netra checks real availability, follows every clinic rule, reads the details back, and books only after you say yes.</p>
              <Link to="/login" className="btn mt-8 bg-white text-slate-900 hover:bg-brand-50">Log in to try it <ArrowRight className="h-4 w-4" /></Link>
            </div>
            <div className="space-y-3">
              {[
                ["you", "Which doctor treats glaucoma?"],
                ["netra", "Dr. Meera Iyer covers glaucoma. She's in OPD Monday, Wednesday, Friday and Saturday."],
                ["you", "Book her this Friday at 11 AM."],
                ["netra", "A new glaucoma consultation with Dr. Iyer on Friday at 11:00 AM. Shall I book it?"],
              ].map(([who, text], i) => (
                <div key={i} className={`flex ${who === "you" ? "justify-end" : ""}`}>
                  <p className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${who === "you" ? "rounded-br-sm bg-brand-500" : "rounded-bl-sm bg-white/10"}`}>{text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 py-8 text-sm text-slate-500 sm:flex-row sm:px-6">
          <Logo />
          <p>NetraCare is a fictional clinic for a capstone project. All data is synthetic.</p>
        </div>
      </footer>
    </main>
  );
}
