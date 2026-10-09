import { useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import type { VaultState } from "../api";

type Variant = "primary" | "secondary" | "danger" | "ghost";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-indigo-600 text-white hover:bg-indigo-700 focus-visible:outline-indigo-600 disabled:bg-indigo-300 dark:hover:bg-indigo-500 dark:focus-visible:outline-indigo-400 dark:disabled:bg-indigo-900 dark:disabled:text-indigo-300",
  secondary: "bg-white text-slate-800 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 disabled:text-slate-400 dark:bg-slate-800 dark:text-slate-100 dark:ring-slate-600 dark:hover:bg-slate-700 dark:disabled:text-slate-500",
  danger: "bg-red-600 text-white hover:bg-red-700 focus-visible:outline-red-600 disabled:bg-red-300 dark:hover:bg-red-500 dark:focus-visible:outline-red-400 dark:disabled:bg-red-900 dark:disabled:text-red-300",
  ghost: "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
};

export function Button({
  variant = "primary",
  className = "",
  busy = false,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; busy?: boolean }) {
  return (
    <button
      {...props}
      disabled={props.disabled || busy}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold shadow-sm transition focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed ${VARIANTS[variant]} ${className}`}
    >
      {busy && <Spinner />}
      {children}
    </button>
  );
}

export function Spinner() {
  return <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden />;
}

export function Card({ title, subtitle, children, actions, className = "" }: {
  title?: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-6 dark:bg-slate-900 dark:shadow-none dark:ring-slate-800 ${className}`}>
      {(title || actions) && (
        <header className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{title}</h2>}
            {subtitle && <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

const ALERTS = {
  info: "bg-indigo-50 text-indigo-900 ring-indigo-200 dark:bg-indigo-500/10 dark:text-indigo-200 dark:ring-indigo-500/30",
  success: "bg-emerald-50 text-emerald-900 ring-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-200 dark:ring-emerald-500/30",
  warning: "bg-amber-50 text-amber-900 ring-amber-200 dark:bg-amber-500/10 dark:text-amber-200 dark:ring-amber-500/30",
  error: "bg-red-50 text-red-900 ring-red-200 dark:bg-red-500/10 dark:text-red-200 dark:ring-red-500/30",
};

export function Alert({ kind = "info", children }: { kind?: keyof typeof ALERTS; children: ReactNode }) {
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`rounded-lg p-3 text-sm ring-1 ring-inset ${ALERTS[kind]}`}>
      {children}
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="block text-sm font-medium text-slate-800 dark:text-slate-200">{label}</span>
      <div className="mt-1">{children}</div>
      {hint && <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">{hint}</span>}
    </label>
  );
}

export const inputClass =
  "block w-full rounded-lg border-0 bg-white px-3 py-2 text-slate-900 shadow-sm ring-1 ring-inset ring-slate-300 placeholder:text-slate-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm dark:bg-slate-950 dark:text-slate-100 dark:ring-slate-700 dark:placeholder:text-slate-500 dark:focus:ring-indigo-400";

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      type="button"
      variant="secondary"
      className="!px-2.5 !py-1 text-xs"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
    >
      {copied ? "Copied" : label}
    </Button>
  );
}

export function Mono({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <pre className={`overflow-x-auto rounded-lg bg-slate-900 p-3 font-mono text-xs leading-relaxed text-slate-100 dark:bg-slate-950 dark:ring-1 dark:ring-slate-800 ${className}`}>
      {children}
    </pre>
  );
}

const STATE_STYLES: Record<VaultState, string> = {
  setup: "bg-slate-100 text-slate-700 ring-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-600",
  active: "bg-emerald-100 text-emerald-800 ring-emerald-300 dark:bg-emerald-500/15 dark:text-emerald-300 dark:ring-emerald-500/40",
  warning: "bg-amber-100 text-amber-800 ring-amber-300 dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-500/40",
  grace: "bg-orange-100 text-orange-800 ring-orange-300 dark:bg-orange-500/15 dark:text-orange-300 dark:ring-orange-500/40",
  released: "bg-red-100 text-red-800 ring-red-300 dark:bg-red-500/15 dark:text-red-300 dark:ring-red-500/40",
};
const STATE_LABELS: Record<VaultState, string> = {
  setup: "Setup",
  active: "Active",
  warning: "Warning",
  grace: "Grace",
  released: "Released",
};

/** One colour scheme everywhere: Active green, Warning amber, Grace orange, Released red. */
export function StateBadge({ state, large = false }: { state: VaultState; large?: boolean }) {
  return (
    <span
      data-testid="state-badge"
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold ring-1 ring-inset ${STATE_STYLES[state]} ${large ? "px-3 py-1 text-base" : "px-2.5 py-0.5 text-xs"}`}
    >
      <span className="h-2 w-2 rounded-full bg-current" aria-hidden />
      {STATE_LABELS[state]}
    </span>
  );
}

export function formatDuration(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${sec}s`;
  return `${m}:${String(sec).padStart(2, "0")}`;
}
