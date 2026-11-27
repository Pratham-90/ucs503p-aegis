import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { ThemeToggle } from "./ThemeToggle";

export function Logo({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <defs>
        <linearGradient id="aegis-shield" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#6366f1" />
          <stop offset="1" stopColor="#4338ca" />
        </linearGradient>
      </defs>
      <path d="M32 4 8 13v17c0 15 10 26 24 30 14-4 24-15 24-30V13L32 4Z" className="fill-slate-800 dark:fill-slate-700" />
      <path d="M32 12 15 18.5V30c0 10.5 7 18.6 17 21.8 10-3.2 17-11.3 17-21.8V18.5L32 12Z" fill="url(#aegis-shield)" />
      <rect x="25" y="28" width="14" height="11" rx="2" fill="#fff" />
      <path d="M28 28v-3a4 4 0 0 1 8 0v3" stroke="#fff" strokeWidth="2.5" fill="none" />
    </svg>
  );
}

const itemClass = "whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition";
const idleClass =
  "text-slate-600 hover:bg-slate-900/5 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white";
const navClass = ({ isActive }: { isActive: boolean }) =>
  `${itemClass} ${isActive ? "bg-slate-900 text-white shadow-sm dark:bg-white dark:text-slate-900" : idleClass}`;

export function Layout() {
  const { owner, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="relative z-40 px-3 pt-3 sm:px-4 md:sticky md:top-0">
        <div className="glass-strong mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 rounded-2xl px-3 py-2 sm:px-4">
          <Link to="/" className="flex items-center gap-2 text-base font-semibold tracking-tight text-slate-900 dark:text-white">
            <Logo /> Aegis
          </Link>
          <nav className="-mx-1 flex w-full items-center gap-0.5 overflow-x-auto px-1 pb-0.5 [scrollbar-width:none] md:mx-0 [&::-webkit-scrollbar]:hidden md:w-auto md:overflow-visible md:px-0 md:pb-0">
            {owner && <NavLink to="/dashboard" className={navClass}>Dashboard</NavLink>}
            <NavLink to="/trustee" className={navClass}>Trustee</NavLink>
            <NavLink to="/recover" className={navClass}>Recovery Room</NavLink>
            <NavLink to="/demo" className={navClass}>Demo Console</NavLink>
            {owner ? (
              <button
                className={`${itemClass} ${idleClass}`}
                onClick={async () => {
                  await logout();
                  navigate("/");
                }}
              >
                Log out
              </button>
            ) : (
              <NavLink to="/login" className={navClass}>Log in</NavLink>
            )}
            <span className="mx-1 hidden h-5 w-px bg-slate-900/10 md:block dark:bg-white/10" aria-hidden />
            <ThemeToggle />
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:py-10">
        <Outlet />
      </main>
      <footer className="mx-auto w-full max-w-6xl px-4 pb-8">
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-900/10 pt-5 text-xs text-slate-500 dark:border-white/10 dark:text-slate-400">
          <span>Aegis prototype · UCS503P, TIET 2026–27</span>
          <span>The server stores only ciphertext and encrypted shares; it can never read a vault on its own.</span>
        </div>
      </footer>
    </div>
  );
}
