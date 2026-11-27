import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { VaultState } from "../api";
import { useAuth } from "../auth";
import { buttonClass, StateBadge } from "../components/ui";

const STEPS = [
  { title: "Encrypt", body: "Your browser encrypts the message or file with AES-256-GCM. The key never leaves your device." },
  { title: "Split", body: "The key is split with Shamir's Secret Sharing: any K of your N trustees can rebuild it, K−1 learn nothing." },
  { title: "Check in", body: "Aegis asks you to check in on a schedule. One click resets the clock and the vault stays sealed." },
  { title: "Release", body: "If you stop responding and the grace period ends, trustees receive their encrypted shares and K of them open the vault." },
];

const LIFECYCLE: [VaultState, string][] = [
  ["active", "You check in on schedule"],
  ["warning", "A check-in is missed"],
  ["grace", "Last chance to check in"],
  ["released", "Trustees receive their shares"],
];

const SERVER_CAN = ["Keep time and run the release schedule", "Send check-in prompts and release emails", "Store ciphertext and shares encrypted to each trustee"];
const SERVER_NEVER = ["Your message or files", "The AES key that locks them", "Any share in plaintext", "A trustee's private key"];

interface Proof { value: string; label: string; detail: string }

/** Headline numbers from metrics/prototype-metrics.json (published with the build); hidden if absent. */
function useProof(): Proof[] | null {
  const [proof, setProof] = useState<Proof[] | null>(null);
  useEffect(() => {
    fetch("/metrics/prototype-metrics.json")
      .then((r) => (r.ok ? r.json() : null))
      .then((doc) => {
        const m = doc?.metrics;
        if (!m) return;
        const value = (name: string) => m[name]?.value;
        const early = value("NFR-REL-1 early releases (requirement cadence)");
        const findings = value("NFR-SEC-1/5 zero-knowledge inspection findings");
        const vectors = value("Cross-language vectors (Python -> TypeScript)");
        const live = value("NFR-PERF-1 p95 check-in latency (deployed)");
        const items: Proof[] = [];
        if (typeof early === "number") items.push({ value: String(early), label: "early releases", detail: "across 1,000 simulated schedules with injected faults" });
        if (typeof findings === "number") items.push({ value: String(findings), label: "zero-knowledge findings", detail: "scanning everything the server stores and receives" });
        if (typeof vectors === "string") items.push({ value: vectors.split(" ")[0], label: "cross-language vectors", detail: "Python and TypeScript crypto agree on every case" });
        if (live && typeof live.sequential_p95_ms === "number") items.push({ value: `${Math.round(live.sequential_p95_ms)} ms`, label: "p95 check-in, live", detail: "on the deployed site; target 500 ms" });
        setProof(items.length ? items : null);
      })
      .catch(() => setProof(null));
  }, []);
  return proof;
}

function Tick({ ok }: { ok: boolean }) {
  return ok ? (
    <svg viewBox="0 0 20 20" className="mt-0.5 h-4 w-4 flex-none text-emerald-600 dark:text-emerald-400" aria-hidden>
      <path d="M5 10.5 8.5 14 15 6.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ) : (
    <svg viewBox="0 0 20 20" className="mt-0.5 h-4 w-4 flex-none text-slate-400 dark:text-slate-500" aria-hidden>
      <path d="M6 6l8 8M14 6l-8 8" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

/** A miniature of the product itself: the lifecycle the scheduler enforces and a 2-of-3 split. */
function VaultPreview() {
  return (
    <div className="glass-inset rounded-2xl p-5" aria-label="How a vault moves from Active to Released">
      <div className="flex items-center justify-between font-mono text-[11px] uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">
        <span>vault lifecycle</span>
        <span>K = 2 · N = 3</span>
      </div>
      <ol className="mt-4 space-y-3 border-l border-slate-900/10 pl-4 dark:border-white/10">
        {LIFECYCLE.map(([state, text]) => (
          <li key={state} className="flex flex-wrap items-center gap-3">
            <span className="w-24"><StateBadge state={state} /></span>
            <span className="text-sm text-slate-600 dark:text-slate-300">{text}</span>
          </li>
        ))}
      </ol>
      <div className="mt-5 border-t border-slate-900/10 pt-4 dark:border-white/10">
        <div className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">key shares</div>
        <div className="mt-2 grid grid-cols-3 gap-2">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className={`rounded-lg py-2 text-center font-mono text-xs ${
                n < 3
                  ? "bg-indigo-600 text-white shadow-[inset_0_1px_0_rgb(255_255_255/0.2),0_6px_16px_-8px_rgb(79_70_229/0.8)]"
                  : "glass-inset text-slate-400 dark:text-slate-500"
              }`}
            >
              share {n}
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Any two rebuild the key. One alone reveals nothing.</p>
      </div>
    </div>
  );
}

export function Landing() {
  const { owner } = useAuth();
  const proof = useProof();
  return (
    <div className="space-y-14">
      <section className="glass relative overflow-hidden rounded-3xl px-6 py-10 sm:px-10 sm:py-14">
        <div
          className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-indigo-500/25 blur-3xl dark:bg-indigo-500/20"
          aria-hidden
        />
        <div className="relative grid items-center gap-10 lg:grid-cols-[1.3fr_1fr]">
          <div>
            <p className="glass-inset inline-flex items-center gap-2 rounded-full px-3 py-1 font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-indigo-700 dark:text-indigo-300">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" aria-hidden />
              Encrypted dead-man's switch
            </p>
            <h1 className="mt-5 text-balance text-4xl font-semibold leading-[1.05] tracking-[-0.03em] text-slate-900 sm:text-5xl dark:text-white">
              Your secrets reach the right people, only when you no longer can.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg dark:text-slate-300">
              Miss your check-ins and, after a grace period, your trustees can open what you left them. No one opens it
              early, no single person can open it alone, and the server never can.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to={owner ? "/dashboard" : "/register"} className={buttonClass("primary", "px-5 py-2.5")}>
                {owner ? "Go to your dashboard" : "Create your vault"}
              </Link>
              <Link to="/demo" className={buttonClass("secondary", "px-5 py-2.5")}>
                Open the demo console
              </Link>
            </div>
          </div>
          <VaultPreview />
        </div>
      </section>

      {proof && (
        <section aria-label="Measured results">
          <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {proof.map((p) => (
              <div key={p.label} className="glass rounded-2xl p-5">
                <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">{p.label}</dt>
                <dd className="mt-1 font-mono text-3xl font-semibold tracking-tight text-slate-900 dark:text-white">{p.value}</dd>
                <dd className="mt-1 text-xs text-slate-500 dark:text-slate-400">{p.detail}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">Every number above was measured by a script in the repository.</p>
        </section>
      )}

      <section>
        <h2 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">How it works</h2>
        <ol className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <li key={s.title} className="glass rounded-2xl p-5">
              <span className="font-mono text-xs font-medium text-indigo-600 dark:text-indigo-300">{String(i + 1).padStart(2, "0")}</span>
              <h3 className="mt-3 font-semibold text-slate-900 dark:text-white">{s.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{s.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="glass grid gap-8 rounded-2xl p-6 sm:p-8 md:grid-cols-[1fr_1fr_1fr]">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">The trust model</h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
            The server is trusted to keep time and deliver messages, never to read your vault. Decryption needs K
            trustees' private keys, which exist only on their own devices.
          </p>
        </div>
        <div>
          <h3 className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">The server can</h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-700 dark:text-slate-300">
            {SERVER_CAN.map((s) => <li key={s} className="flex gap-2"><Tick ok />{s}</li>)}
          </ul>
        </div>
        <div>
          <h3 className="font-mono text-[11px] uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">The server never sees</h3>
          <ul className="mt-3 space-y-2 text-sm text-slate-700 dark:text-slate-300">
            {SERVER_NEVER.map((s) => <li key={s} className="flex gap-2"><Tick ok={false} />{s}</li>)}
          </ul>
        </div>
      </section>
    </div>
  );
}
