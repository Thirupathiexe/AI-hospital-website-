// All calls go to our FastAPI backend. The login cookie is HttpOnly, so JavaScript never sees the token.
export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request(method, path, body) {
  const res = await fetch(`/api${path}`, {
    method,
    credentials: "same-origin",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail || {};
    throw new ApiError(res.status, d.code || "ERROR", d.message || "Something went wrong. Please try again.");
  }
  return data;
}

const qs = (params) => {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => v && p.set(k, v));
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const api = {
  login: (body) => request("POST", "/login", body),
  logout: () => request("POST", "/logout"),
  me: () => request("GET", "/me"),
  clock: () => request("GET", "/clock"),
  doctors: () => request("GET", "/doctors"),
  holidays: () => request("GET", "/holidays"),
  slots: (params) => request("GET", `/slots${qs(params)}`),
  appointments: (params = {}) => request("GET", `/appointments${qs(params)}`),
  book: (body) => request("POST", "/appointments", body),
  cancel: (id) => request("POST", `/appointments/${encodeURIComponent(id)}/cancel`),
  reschedule: (id, body) => request("POST", `/appointments/${encodeURIComponent(id)}/reschedule`, body),
  complete: (id) => request("POST", `/appointments/${encodeURIComponent(id)}/complete`),
  patients: (q) => request("GET", `/patients${qs({ q })}`),
  addPatient: (body) => request("POST", "/patients", body),
  chat: (body) => request("POST", "/assistant/chat", body),
  assistantStatus: () => request("GET", "/assistant/status"),
};

export const fmtTime = (hhmm) => {
  const [h, m] = hhmm.split(":").map(Number);
  const ampm = h >= 12 ? "PM" : "AM";
  return `${((h + 11) % 12) + 1}:${String(m).padStart(2, "0")} ${ampm}`;
};

export const fmtDate = (iso, opts = { weekday: "short", day: "numeric", month: "short" }) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", opts);

export const addDays = (iso, n) => {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + n);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
