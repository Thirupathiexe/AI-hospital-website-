import { LogOut, Menu, X } from "lucide-react";
import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { Logo } from "./ui";

export default function Navbar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const onLanding = pathname === "/";

  const doLogout = async () => {
    await logout();
    nav("/");
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/60 bg-white/80 backdrop-blur-xl">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Link to="/" aria-label="NetraCare home"><Logo /></Link>
        {onLanding && (
          <div className="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex">
            <a href="#services" className="hover:text-brand-700">Services</a>
            <a href="#doctors" className="hover:text-brand-700">Doctors</a>
            <a href="#timings" className="hover:text-brand-700">Timings</a>
            <a href="#voice" className="hover:text-brand-700">Voice booking</a>
          </div>
        )}
        <div className="hidden items-center gap-3 md:flex">
          {user ? (
            <>
              <Link to={`/${user.role}`} className="btn-ghost">
                <span className="grid h-6 w-6 place-items-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">{user.name?.[0] ?? "?"}</span>
                {user.name} <span className="text-xs capitalize text-slate-400">· {user.role}</span>
              </Link>
              <button onClick={doLogout} className="btn-ghost" aria-label="Log out"><LogOut className="h-4 w-4" /></button>
            </>
          ) : (
            <>
              <Link to="/login" className="btn-ghost">Log in</Link>
              <Link to="/login" className="btn-primary">Book appointment</Link>
            </>
          )}
        </div>
        <button className="md:hidden" onClick={() => setOpen(!open)} aria-label="Menu">{open ? <X /> : <Menu />}</button>
      </nav>
      {open && (
        <div className="flex flex-col gap-2 border-t border-slate-100 bg-white px-4 py-4 md:hidden" onClick={() => setOpen(false)}>
          {user ? (
            <>
              <Link to={`/${user.role}`} className="btn-ghost">My dashboard</Link>
              <button onClick={doLogout} className="btn-ghost">Log out</button>
            </>
          ) : (
            <Link to="/login" className="btn-primary">Log in / Book</Link>
          )}
        </div>
      )}
    </header>
  );
}
