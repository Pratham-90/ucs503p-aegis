import { useCallback, useEffect, useState, type ReactNode } from "react";
import { api, errorMessage, type ServerView, type VaultState } from "../api";
import { Alert, Button, Card, Field, inputClass, Mono, StateBadge } from "../components/ui";

interface Email { id: string; to: string; subject: string; body: string; kind: string; status: string; created_at: string }
interface Tick { id: string; trigger: string; started_at: string; vaults_checked: number; transitions: { vault_id: string; from_state: string; to_state: string; actions: string[] }[] }
interface DemoVault { id: string; owner_email: string; state: VaultState; k: number; n: number; deadline_at: string | null }
interface Metric { value: unknown; target?: string; met?: boolean | null; unit?: string; environment?: string }

const TOKEN_KEY = "aegis.demoToken";

/** Turn URLs in an email body into links, so the in-app outbox works like a mailbox. */
function linkify(text: string): ReactNode[] {
  return text.split(/(https?:\/\/\S+)/g).map((part, i) =>
    /^https?:\/\//.test(part) ? (
      <a key={i} href={part.replace(/^https?:\/\/[^/]+/, "")} className="break-all font-medium text-indigo-700 dark:text-indigo-300 underline">{part}</a>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

export function DemoConsole() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY) ?? "");
  const [draft, setDraft] = useState("");
  const [emails, setEmails] = useState<Email[]>([]);
  const [ticks, setTicks] = useState<Tick[]>([]);
  const [vaults, setVaults] = useState<DemoVault[]>([]);
  const [clock, setClock] = useState<{ offset_s: number; server_now: string } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<ServerView | null>(null);
  const [metrics, setMetrics] = useState<Record<string, Metric> | null>(null);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const headers = { "X-Demo-Token": token };

  const load = useCallback(async () => {
    if (!token) return;
    const h = { "X-Demo-Token": token };
    try {
      const [o, t, v, c] = await Promise.all([
        api.get<{ emails: Email[] }>("/demo/outbox", h),
        api.get<{ ticks: Tick[] }>("/demo/ticks?limit=20", h),
        api.get<{ vaults: DemoVault[] }>("/demo/vaults", h),
        api.get<{ offset_s: number; server_now: string }>("/demo/clock", h),
      ]);
      setEmails(o.emails);
      setTicks(t.ticks);
      setVaults(v.vaults);
      setClock(c);
    } catch (e) {
      setMessage({ kind: "error", text: errorMessage(e) });
    }
  }, [token]);

  useEffect(() => {
    void load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  useEffect(() => {
    fetch("/metrics/prototype-metrics.json")
      .then((r) => (r.ok ? r.json() : null))
      .then((m) => setMetrics(m?.metrics ?? null))
      .catch(() => setMetrics(null));
  }, []);

  useEffect(() => {
    if (!selected || !token) return setView(null);
    api.get<ServerView>(`/demo/server-view/${selected}`, { "X-Demo-Token": token }).then(setView).catch(() => setView(null));
  }, [selected, token, ticks]);

  async function act(name: string, fn: () => Promise<string>) {
    setBusy(name);
    setMessage(null);
    try {
      setMessage({ kind: "success", text: await fn() });
      await load();
    } catch (e) {
      setMessage({ kind: "error", text: errorMessage(e) });
    } finally {
      setBusy(null);
    }
  }

  const runTick = () =>
    act("tick", async () => {
      const r = await api.post<{ transitions: unknown[]; emails_delivered: number }>("/demo/tick", {}, headers);
      return `Tick done: ${r.transitions.length} transition(s), ${r.emails_delivered} email(s) delivered.`;
    });
  const advance = (seconds: number) =>
    act(`adv${seconds}`, async () => {
      await api.post("/demo/clock/advance", { seconds }, headers);
      return `Server clock moved forward ${seconds} s (demo only). Run a tick to apply.`;
    });

  if (!token) {
    return (
      <div className="mx-auto max-w-md">
        <Card title="Demo Console" subtitle="Enter the DEMO_ADMIN_TOKEN configured on the server.">
          <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); sessionStorage.setItem(TOKEN_KEY, draft); setToken(draft); }}>
            <Field label="Demo admin token">
              <input aria-label="Demo admin token" className={inputClass} type="password" value={draft} onChange={(e) => setDraft(e.target.value)} />
            </Field>
            <Button type="submit">Open console</Button>
          </form>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Demo Console</h1>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Server time {clock ? new Date(clock.server_now).toLocaleTimeString() : "…"}
            {clock && clock.offset_s > 0 && <> (fast-forwarded {clock.offset_s} s)</>}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={runTick} busy={busy === "tick"} data-testid="run-tick">Run tick now</Button>
          <Button variant="secondary" onClick={() => advance(60)} busy={busy === "adv60"}>+1 min</Button>
          <Button variant="secondary" onClick={() => advance(300)} busy={busy === "adv300"}>+5 min</Button>
          <Button variant="secondary" onClick={() => act("reset-clock", async () => { await api.post("/demo/clock/reset", {}, headers); return "Clock offset cleared."; })}>
            Reset clock
          </Button>
          <Button
            variant="danger"
            onClick={() => window.confirm("Delete ALL demo data?") && act("reset", async () => { await api.post("/demo/reset", {}, headers); return "Demo data reset."; })}
          >
            Reset demo data
          </Button>
          <Button variant="ghost" onClick={() => { sessionStorage.removeItem(TOKEN_KEY); setToken(""); }}>Lock</Button>
        </div>
      </div>
      {message && <Alert kind={message.kind}>{message.text}</Alert>}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title={`Outbox (${emails.length})`} subtitle="Every email the system decided to send (in-app mailbox).">
          <ul className="max-h-[32rem] space-y-3 overflow-y-auto pr-1" data-testid="outbox">
            {emails.map((e) => (
              <li key={e.id} className="rounded-lg p-3 text-sm ring-1 ring-slate-200 dark:ring-slate-700">
                <div className="flex flex-wrap justify-between gap-2">
                  <span className="font-semibold">{e.subject}</span>
                  <span className="text-xs text-slate-500 dark:text-slate-400">{e.kind} · {e.status}</span>
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400">to {e.to} · {new Date(e.created_at).toLocaleTimeString()}</div>
                <p className="mt-2 whitespace-pre-wrap text-slate-700 dark:text-slate-300">{linkify(e.body)}</p>
              </li>
            ))}
            {emails.length === 0 && <li className="text-sm text-slate-500 dark:text-slate-400">No emails yet.</li>}
          </ul>
        </Card>
        <div className="space-y-6">
          <Card title="Vaults">
            <ul className="space-y-2 text-sm">
              {vaults.map((v) => (
                <li key={v.id} className="flex flex-wrap items-center justify-between gap-2">
                  <span>{v.owner_email} · {v.k}/{v.n}</span>
                  <span className="flex items-center gap-2">
                    <StateBadge state={v.state} />
                    <Button variant="secondary" className="!px-2 !py-1 text-xs" onClick={() => setSelected(selected === v.id ? null : v.id)}>
                      {selected === v.id ? "Hide" : "Server view"}
                    </Button>
                  </span>
                </li>
              ))}
              {vaults.length === 0 && <li className="text-slate-500 dark:text-slate-400">No vaults.</li>}
            </ul>
            {view && <Mono className="mt-4 max-h-96">{JSON.stringify(view, null, 2)}</Mono>}
          </Card>
          <Card title="Scheduler tick log">
            <ul className="max-h-72 space-y-2 overflow-y-auto text-xs">
              {ticks.map((t) => (
                <li key={t.id} className="rounded bg-slate-50 dark:bg-slate-800/50 p-2 ring-1 ring-slate-200 dark:ring-slate-700">
                  <span className="font-mono">{new Date(t.started_at).toLocaleTimeString()}</span> · {t.trigger} · checked {t.vaults_checked}
                  {t.transitions.map((tr) => (
                    <div key={tr.vault_id + tr.to_state} className="mt-1 text-slate-700 dark:text-slate-300">
                      {tr.from_state} → <strong>{tr.to_state}</strong> ({tr.actions.join(", ")})
                    </div>
                  ))}
                </li>
              ))}
              {ticks.length === 0 && <li className="text-slate-500 dark:text-slate-400">No ticks yet.</li>}
            </ul>
          </Card>
        </div>
      </div>

      <Card title="Measured results" subtitle="From metrics/prototype-metrics.json (every value produced by a script that was actually run).">
        {metrics ? (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead><tr className="text-left text-slate-500 dark:text-slate-400"><th className="py-1 pr-4">Metric</th><th className="pr-4">Value</th><th className="pr-4">Target</th><th>Met</th></tr></thead>
              <tbody>
                {Object.entries(metrics).map(([name, m]) => (
                  <tr key={name} className="border-t border-slate-100 dark:border-slate-800">
                    <td className="py-1 pr-4 font-medium">{name}</td>
                    <td className="pr-4 font-mono">{typeof m.value === "object" ? JSON.stringify(m.value) : String(m.value)}{m.unit ? ` ${m.unit}` : ""}</td>
                    <td className="pr-4 text-slate-600 dark:text-slate-400">{m.target ?? "—"}</td>
                    <td>{m.met === true ? "✓" : m.met === false ? "✗" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-slate-500 dark:text-slate-400">No metrics file published with this build.</p>
        )}
      </Card>
    </div>
  );
}
