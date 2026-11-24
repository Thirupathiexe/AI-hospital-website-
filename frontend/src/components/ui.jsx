import { AlertCircle, CheckCircle2, Loader2, X } from "lucide-react";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

export const Spinner = ({ className = "h-6 w-6" }) => <Loader2 className={`animate-spin text-brand-600 ${className}`} />;

export function Logo({ light = false }) {
  return (
    <span className="flex items-center gap-2.5">
      <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 shadow-lg shadow-brand-600/30">
        <svg viewBox="0 0 64 64" className="h-6 w-6"><path d="M6 32s10-15 26-15 26 15 26 15-10 15-26 15S6 32 6 32z" fill="#fff" /><circle cx="32" cy="32" r="8" fill="#0d8079" /><circle cx="35" cy="29" r="2.5" fill="#fff" /></svg>
      </span>
      <span className={`text-lg font-extrabold tracking-tight ${light ? "text-white" : "text-ink"}`}>
        Netra<span className="text-brand-500">Care</span>
      </span>
    </span>
  );
}

const STATUS = {
  booked: "bg-brand-50 text-brand-700 ring-brand-200",
  completed: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  cancelled: "bg-slate-100 text-slate-500 ring-slate-200",
};
export const StatusBadge = ({ status }) => (
  <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ring-1 ${STATUS[status] || STATUS.cancelled}`}>{status}</span>
);

export function Alert({ kind = "error", children, onClose }) {
  if (!children) return null;
  const err = kind === "error";
  return (
    <div role="alert" className={`flex items-start gap-3 rounded-xl px-4 py-3 text-sm ${err ? "bg-rose-50 text-rose-800 ring-1 ring-rose-200" : "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200"}`}>
      {err ? <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /> : <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />}
      <div className="flex-1">{children}</div>
      {onClose && <button onClick={onClose} aria-label="Dismiss"><X className="h-4 w-4 opacity-60 hover:opacity-100" /></button>}
    </div>
  );
}

// Simple toast notifications
const ToastCtx = createContext(() => {});
export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);
  const push = useCallback((message, kind = "success") => {
    const id = Math.random().toString(36).slice(2);
    setItems((x) => [...x, { id, message, kind }]);
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), 5000);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed left-1/2 top-20 z-[60] flex w-[min(92vw,420px)] -translate-x-1/2 flex-col gap-2">
        {items.map((t) => <Alert key={t.id} kind={t.kind}>{t.message}</Alert>)}
      </div>
    </ToastCtx.Provider>
  );
}
export const useToast = () => useContext(ToastCtx);

export function useAppointmentsRefresh(callback) {
  // The voice assistant fires this event when it books or cancels, so tables refresh themselves.
  useEffect(() => {
    window.addEventListener("netracare:changed", callback);
    return () => window.removeEventListener("netracare:changed", callback);
  }, [callback]);
}

export function PageHeader({ eyebrow, title, children }) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-600">{eyebrow}</p>
        <h1 className="mt-1 text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1>
      </div>
      {children}
    </div>
  );
}

export const Empty = ({ icon: Icon, title, text }) => (
  <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
    {Icon && <Icon className="h-10 w-10 text-slate-300" />}
    <p className="font-semibold text-slate-700">{title}</p>
    {text && <p className="max-w-sm text-sm text-slate-500">{text}</p>}
  </div>
);
