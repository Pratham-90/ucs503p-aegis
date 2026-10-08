import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage, type ServerView, type VaultSummary } from "../api";
import { Countdown } from "../components/Countdown";
import { Alert, Button, Card, formatDuration, Mono, StateBadge } from "../components/ui";

const EXPLAIN: Record<string, string> = {
  active: "Sealed. Check in before the deadline to keep it that way.",
  warning: "Your check-in is due. A prompt has been emailed. One click below resets the timer.",
  grace: "You missed the deadline. The vault is in its grace period. Check in now to keep it sealed.",
  released: "Released. Your trustees have been sent their encrypted shares; K of them can now open the vault.",
};

export function Dashboard() {
  const [vault, setVault] = useState<VaultSummary | null | undefined>(undefined);
  const [offsetMs, setOffsetMs] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const [serverView, setServerView] = useState<ServerView | null>(null);

  const load = useCallback(async () => {
    try {
      const { vault } = await api.get<{ vault: VaultSummary | null }>("/vaults/mine");
      setVault(vault);
      if (vault) setOffsetMs(new Date(vault.server_now).getTime() - Date.now());
      setError(null);
    } catch (e) {
      setError(errorMessage(e));
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [load]);

  async function checkIn() {
    if (!vault) return;
    setBusy(true);
    setFlash(null);
    try {
      const { vault: updated } = await api.post<{ vault: VaultSummary }>(`/vaults/${vault.id}/checkin`);
      setVault(updated);
      setOffsetMs(new Date(updated.server_now).getTime() - Date.now());
      setFlash("Checked in. The timer has been reset.");
    } catch (e) {
      setError(errorMessage(e));
      void load();
    } finally {
      setBusy(false);
    }
  }

  async function toggleServerView() {
    if (serverView || !vault) return setServerView(null);
    setServerView(await api.get<ServerView>(`/vaults/${vault.id}/server-view`));
  }

  if (vault === undefined) return <p className="text-sm text-slate-500">Loading your vault…</p>;
  if (vault === null) {
    return (
      <Card title="You don't have a vault yet" subtitle="Create one: choose trustees, a threshold and a check-in schedule.">
        <Link to="/vault/new" className="inline-flex rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
          Create my vault
        </Link>
      </Card>
    );
  }

  const enrolled = vault.trustees.filter((t) => t.enrolled).length;
  return (
    <div className="space-y-6">
      {error && <Alert kind="error">{error}</Alert>}
      {vault.state === "setup" ? (
        <Card title="Vault setup in progress" actions={<StateBadge state="setup" large />}>
          <p className="text-sm text-slate-700">
            {enrolled} of {vault.n} trustees have enrolled. Once all of them have, encrypt and upload your secret to
            arm the vault.
          </p>
          <Link to="/vault/new" className="mt-4 inline-flex rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            Continue setup
          </Link>
        </Card>
      ) : (
        <Card
          title={<span className="flex items-center gap-3">Your vault <StateBadge state={vault.state} large /></span>}
          subtitle={EXPLAIN[vault.state]}
        >
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {vault.state !== "released" && (
              <>
                <Countdown label="next check-in due" target={vault.deadline_at} offsetMs={offsetMs} />
                <Countdown label="release if no check-in" target={vault.release_at} offsetMs={offsetMs} />
              </>
            )}
            <div className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
              <div className="text-xs font-medium uppercase tracking-wide text-slate-500">threshold</div>
              <div className="mt-1 text-2xl font-semibold text-slate-900">
                {vault.k} of {vault.n}
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {vault.loss_tolerance} trustee{vault.loss_tolerance === 1 ? "" : "s"} can be lost
              </div>
            </div>
          </div>
          {vault.state !== "released" && (
            <div className="mt-6 flex flex-wrap items-center gap-4">
              <Button onClick={checkIn} busy={busy} className="!px-6 !py-3 text-base" data-testid="checkin-button">
                I'm OK — check in
              </Button>
              <span className="text-sm text-slate-600">
                Every {formatDuration(vault.interval_s)}, then {formatDuration(vault.grace_s)} grace.
              </span>
            </div>
          )}
          {flash && <div className="mt-4"><Alert kind="success">{flash}</Alert></div>}
          {vault.warnings.map((w) => (
            <div key={w} className="mt-4"><Alert kind="warning">{w}</Alert></div>
          ))}
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Trustees" subtitle="Each holds one encrypted share; their private key never leaves their device.">
          <ul className="divide-y divide-slate-100">
            {vault.trustees.map((t) => (
              <li key={t.id} className="flex items-center justify-between py-2 text-sm">
                <span>
                  <span className="mr-2 font-mono text-slate-400">#{t.position}</span>
                  {t.email}
                </span>
                <span className={t.enrolled ? "text-emerald-700" : "text-amber-700"}>{t.enrolled ? "key enrolled" : "pending"}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Check-in history">
          {vault.checkins.length === 0 ? (
            <p className="text-sm text-slate-500">No check-ins yet.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {vault.checkins.map((c) => (
                <li key={c.at} className="flex justify-between">
                  <span>{new Date(c.at).toLocaleString()}</span>
                  <span className="text-slate-500">{c.source}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {vault.payload_uploaded && (
        <Card
          title="What the server stores"
          subtitle="The raw row for your vault. Ciphertext and encrypted shares only."
          actions={<Button variant="secondary" onClick={toggleServerView}>{serverView ? "Hide" : "Show"}</Button>}
        >
          {serverView && <Mono>{JSON.stringify(serverView, null, 2)}</Mono>}
        </Card>
      )}
    </div>
  );
}
