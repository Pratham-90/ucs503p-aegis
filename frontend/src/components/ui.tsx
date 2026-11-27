import { useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import type { VaultState } from "../api";

type Variant = "primary" | "secondary" | "danger" | "ghost";
const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-indigo-600 text-white shadow-[inset_0_1px_0_rgb(255_255_255/0.2),0_8px_20px_-8px_rgb(79_70_229/0.7)] hover:bg-indigo-500 focus-visible:outline-indigo-500 disabled:bg-indigo-600/40 disabled:text-white/70 disabled:shadow-none",
  secondary:
    "glass-inset text-slate-800 hover:bg-white/80 focus-visible:outline-indigo-500 disabled:text-slate-400 dark:text-slate-100 dark:hover:bg-white/10 dark:disabled:text-slate-500",
  danger:
    "bg-red-600 text-white shadow-[inset_0_1px_0_rgb(255_255_255/0.18)] hover:bg-red-500 focus-visible:outline-red-500 disabled:bg-red-600/40",
  ghost:
    "text-slate-600 hover:bg-slate-900/5 hover:text-slate-900 focus-visible:outline-indigo-500 dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white",
};

/** Classes for a button, also used for router Links that act as buttons. */
export function buttonClass(variant: Variant = "primary", extra = "") {
  return `inline-flex items-center justify-center gap-2 rounded-xl border border-transparent px-4 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed ${VARIANTS[variant]} ${extra}`;
}

export function Button({
  variant = "primary",
  className = "",
  busy = false,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; busy?: boolean }) {
  return (
    <button {...props} disabled={props.disabled || busy} className={buttonClass(variant, className)}>
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
    <section className={`glass rounded-2xl p-5 sm:p-6 ${className}`}>
      {(title || actions) && (
        <header className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-base font-semibold tracking-tight text-slate-900 dark:text-white">{title}</h2>}
            {subtitle && <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{subtitle}</p>}
          </div>
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

/** Page title block: a small mono eyebrow, the h1 and one line of context. */
export function PageHeader({ eyebrow, title, children, actions }: {
  eyebrow: string;
  title: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-3xl">
        <p className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-indigo-600 dark:text-indigo-300">{eyebrow}</p>
        <h1 className="mt-1.5 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl dark:text-white">{title}</h1>
        {children && <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{children}</p>}
      </div>
      {actions}
    </div>
  );
}

const ALERTS = {
  info: "bg-indigo-500/10 text-indigo-950 ring-indigo-500/20 dark:text-indigo-100 dark:ring-indigo-400/25",
  success: "bg-emerald-500/10 text-emerald-950 ring-emerald-600/20 dark:text-emerald-100 dark:ring-emerald-400/25",
  warning: "bg-amber-500/12 text-amber-950 ring-amber-600/25 dark:text-amber-100 dark:ring-amber-400/25",
  error: "bg-red-500/10 text-red-950 ring-red-600/20 dark:text-red-100 dark:ring-red-400/25",
};
const ALERT_BARS = {
  info: "bg-indigo-500",
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  error: "bg-red-500",
};

export function Alert({ kind = "info", children }: { kind?: keyof typeof ALERTS; children: ReactNode }) {
  return (
    <div
      role={kind === "error" ? "alert" : "status"}
      className={`relative overflow-hidden rounded-xl py-3 pl-4 pr-3 text-sm ring-1 ring-inset backdrop-blur-sm ${ALERTS[kind]}`}
    >
      <span className={`absolute inset-y-0 left-0 w-1 ${ALERT_BARS[kind]}`} aria-hidden />
      {children}
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="block text-sm font-medium text-slate-700 dark:text-slate-300">{label}</span>
      <div className="mt-1.5">{children}</div>
      {hint && <span className="mt-1.5 block text-xs text-slate-500 dark:text-slate-400">{hint}</span>}
    </label>
  );
}

export const inputClass =
  "block w-full rounded-xl border border-slate-900/10 bg-white/70 px-3 py-2 text-slate-900 shadow-[inset_0_1px_2px_rgb(15_23_42/0.06)] outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/15 sm:text-sm dark:border-white/10 dark:bg-slate-950/50 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-indigo-400 dark:focus:ring-indigo-400/20";

export const fileInputClass =
  "text-sm text-slate-600 file:mr-3 file:cursor-pointer file:rounded-lg file:border-0 file:bg-slate-900/5 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-slate-800 hover:file:bg-slate-900/10 dark:text-slate-400 dark:file:bg-white/10 dark:file:text-slate-100 dark:hover:file:bg-white/15";

export const linkClass =
  "font-semibold text-indigo-700 underline decoration-indigo-500/30 underline-offset-4 hover:decoration-indigo-500 dark:text-indigo-300";

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

/** Code panels stay dark in both themes, like a terminal. */
export function Mono({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <pre className={`overflow-x-auto rounded-xl bg-slate-950/90 p-4 font-mono text-xs leading-relaxed text-slate-200 ring-1 ring-white/10 ${className}`}>
      {children}
    </pre>
  );
}

const STATE_STYLES: Record<VaultState, string> = {
  setup: "bg-slate-500/10 text-slate-700 ring-slate-500/25 dark:text-slate-300 dark:ring-slate-400/30",
  active: "bg-emerald-500/12 text-emerald-800 ring-emerald-600/25 dark:text-emerald-300 dark:ring-emerald-400/30",
  warning: "bg-amber-500/15 text-amber-800 ring-amber-600/30 dark:text-amber-300 dark:ring-amber-400/30",
  grace: "bg-orange-500/15 text-orange-800 ring-orange-600/30 dark:text-orange-300 dark:ring-orange-400/30",
  released: "bg-red-500/12 text-red-800 ring-red-600/25 dark:text-red-300 dark:ring-red-400/30",
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
  const urgent = state === "warning" || state === "grace";
  return (
    <span
      data-testid="state-badge"
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold ring-1 ring-inset ${STATE_STYLES[state]} ${large ? "px-3 py-1 text-sm" : "px-2.5 py-0.5 text-xs"}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full bg-current ${urgent ? "animate-pulse" : ""}`} aria-hidden />
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
