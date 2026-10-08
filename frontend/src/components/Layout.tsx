import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { ThemeToggle } from "./ThemeToggle";

export function Logo({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <path d="M32 4 8 13v17c0 15 10 26 24 30 14-4 24-15 24-30V13L32 4Z" className="fill-slate-800 dark:fill-slate-600" />
      <path d="M32 12 15 18.5V30c0 10.5 7 18.6 17 21.8 10-3.2 17-11.3 17-21.8V18.5L32 12Z" fill="#4f46e5" />
      <rect x="25" y="28" width="14" height="11" rx="2" fill="#fff" />
      <path d="M28 28v-3a4 4 0 0 1 8 0v3" stroke="#fff" strokeWidth="2.5" fill="none" />
    </svg>
  );
}

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium ${isActive ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900" : "text-slate-700 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800"}`;

export function Layout() {
  const { owner, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3">
          <Link to="/" className="flex items-center gap-2 text-lg font-bold tracking-tight text-slate-900 dark:text-slate-100">
            <Logo /> Aegis
          </Link>
          <nav className="flex flex-wrap items-center gap-1">
            {owner && <NavLink to="/dashboard" className={navClass}>Dashboard</NavLink>}
            <NavLink to="/trustee" className={navClass}>Trustee</NavLink>
            <NavLink to="/recover" className={navClass}>Recovery Room</NavLink>
            <NavLink to="/demo" className={navClass}>Demo Console</NavLink>
            {owner ? (
              <button
                className="rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800"
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
            <ThemeToggle />
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:py-8">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto max-w-6xl px-4 py-4 text-xs text-slate-500 dark:text-slate-400">
          Aegis prototype · UCS503P, TIET 2026–27 · The server stores only ciphertext and encrypted shares; it can
          never read a vault on its own.
        </div>
      </footer>
    </div>
  );
}
