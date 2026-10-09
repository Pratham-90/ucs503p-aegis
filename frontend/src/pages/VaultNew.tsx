import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorMessage, type Invite, type ServerView, type VaultSummary } from "../api";
import { Alert, Button, Card, CopyButton, Field, formatDuration, inputClass, Mono } from "../components/ui";
import { MAX_FILE_BYTES, sealVault, type FileInput, type SealedPayload } from "../crypto/vault";

const PRESETS = [
  { id: "demo", label: "Demo — every 2 min, 1 min grace", interval: 120, grace: 60 },
  { id: "weekly", label: "Weekly — every 7 days, 1 day grace", interval: 7 * 86400, grace: 86400 },
  { id: "monthly", label: "Monthly — every 30 days, 3 days grace", interval: 30 * 86400, grace: 3 * 86400 },
];
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type Step = "configure" | "invite" | "secret" | "review" | "done";

/** FR-4: K >= 2 rejected below, K = N warned, loss tolerance N - K shown. */
export function thresholdFeedback(k: number, n: number) {
  const errors: string[] = [];
  const warnings: string[] = [];
  if (!Number.isInteger(k) || k < 2) errors.push("K must be at least 2 — a single trustee must never be able to open the vault.");
  if (n < 2) errors.push("Add at least two trustees.");
  if (k > n) errors.push(`K cannot exceed the number of trustees (N = ${n}).`);
  if (errors.length === 0 && k === n) {
    warnings.push("K = N: if any single trustee loses their key or becomes unreachable, the vault can never be opened.");
  }
  return { errors, warnings, lossTolerance: Math.max(0, n - k) };
}

function truncate(value: unknown): unknown {
  if (typeof value === "string" && value.length > 64) return `${value.slice(0, 56)}… (${value.length} chars)`;
  if (Array.isArray(value)) return value.map(truncate);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, truncate(v)]));
  return value;
}

export function VaultNew() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("configure");
  const [vault, setVault] = useState<VaultSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // configure
  const [emails, setEmails] = useState(["", "", ""]);
  const [k, setK] = useState(2);
  const [preset, setPreset] = useState("demo");
  const [custom, setCustom] = useState({ interval: 5, grace: 2 });
  // invite
  const [invites, setInvites] = useState<Record<string, Invite>>({});
  // secret (kept in memory only)
  const [message, setMessage] = useState("");
  const [file, setFile] = useState<FileInput | null>(null);
  // done
  const [sent, setSent] = useState<SealedPayload | null>(null);
  const [serverView, setServerView] = useState<ServerView | null>(null);

  const validEmails = emails.map((e) => e.trim().toLowerCase()).filter((e) => EMAIL.test(e));
  const feedback = thresholdFeedback(k, validEmails.length);
  const schedule = useMemo(() => {
    const p = PRESETS.find((x) => x.id === preset);
    return p ? { interval: p.interval, grace: p.grace } : { interval: custom.interval * 60, grace: custom.grace * 60 };
  }, [preset, custom]);

  const loadVault = useCallback(async () => {
    const { vault } = await api.get<{ vault: VaultSummary | null }>("/vaults/mine");
    setVault(vault);
    return vault;
  }, []);

  useEffect(() => {
    loadVault()
      .then((v) => {
        if (v && v.state !== "setup") navigate("/dashboard");
        else if (v) setStep(v.all_enrolled ? "secret" : "invite");
      })
      .catch((e) => setError(errorMessage(e)));
  }, [loadVault, navigate]);

  useEffect(() => {
    if (step !== "invite") return;
    const id = setInterval(() => void loadVault(), 3000);
    return () => clearInterval(id);
  }, [step, loadVault]);

  async function create() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.post<{ vault_id: string; invites: Invite[] }>("/vaults", {
        trustee_emails: validEmails,
        k,
        interval_s: schedule.interval,
        grace_s: schedule.grace,
      });
      setInvites(Object.fromEntries(res.invites.map((i) => [i.trustee_id, i])));
      await loadVault();
      setStep("invite");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function reissue(trusteeId: string) {
    if (!vault) return;
    const invite = await api.post<Invite>(`/vaults/${vault.id}/trustees/${trusteeId}/invite`);
    setInvites((prev) => ({ ...prev, [trusteeId]: invite }));
  }

  async function pickFile(list: FileList | null) {
    const f = list?.[0];
    if (!f) return setFile(null);
    if (f.size > MAX_FILE_BYTES) {
      setError("Files are limited to 1 MB in the prototype.");
      return;
    }
    setFile({ name: f.name, type: f.type || "application/octet-stream", bytes: new Uint8Array(await f.arrayBuffer()) });
    setError(null);
  }

  async function encryptAndUpload() {
    if (!vault) return;
    setBusy(true);
    setError(null);
    try {
      const payload = await sealVault({
        vaultId: vault.id,
        k: vault.k,
        message,
        file,
        trustees: vault.trustees.map((t) => ({ id: t.id, position: t.position, publicJwk: t.public_key_jwk! })),
      });
      const res = await api.post<{ vault: VaultSummary; server_view: ServerView }>(`/vaults/${vault.id}/payload`, payload);
      setSent(payload);
      setServerView(res.server_view);
      setMessage("");
      setFile(null);
      setStep("done");
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const steps: [Step, string][] = [["configure", "Trustees & schedule"], ["invite", "Enrolment"], ["secret", "Secret"], ["review", "Review"], ["done", "Sealed"]];
  return (
    <div className="space-y-6">
      <ol className="flex flex-wrap gap-2 text-xs font-medium">
        {steps.map(([id, label], i) => (
          <li key={id} className={`rounded-full px-3 py-1 ring-1 ${step === id ? "bg-indigo-600 text-white ring-indigo-600" : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-400 ring-slate-200 dark:ring-slate-700"}`}>
            {i + 1}. {label}
          </li>
        ))}
      </ol>
      {error && <Alert kind="error">{error}</Alert>}

      {step === "configure" && (
        <Card title="Trustees, threshold and schedule" subtitle="FR-3, FR-4. The clock starts once the encrypted secret is uploaded.">
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">Trustees (N = {validEmails.length})</h3>
              {emails.map((value, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    aria-label={`Trustee ${i + 1} email`}
                    className={inputClass}
                    type="email"
                    placeholder={`trustee${i + 1}@example.com`}
                    value={value}
                    onChange={(e) => setEmails(emails.map((v, j) => (j === i ? e.target.value : v)))}
                  />
                  {emails.length > 2 && (
                    <Button variant="ghost" type="button" onClick={() => setEmails(emails.filter((_, j) => j !== i))} aria-label="Remove trustee">
                      ✕
                    </Button>
                  )}
                </div>
              ))}
              {emails.length < 10 && (
                <Button variant="secondary" type="button" onClick={() => setEmails([...emails, ""])}>
                  Add trustee
                </Button>
              )}
            </div>
            <div className="space-y-4">
              <Field label="Threshold K (shares needed to open the vault)">
                <input aria-label="Threshold K" className={inputClass} type="number" min={1} max={10} value={k} onChange={(e) => setK(Number(e.target.value))} />
              </Field>
              <div className="text-sm text-slate-700 dark:text-slate-300" data-testid="loss-tolerance">
                <strong>{feedback.lossTolerance}</strong> trustee{feedback.lossTolerance === 1 ? "" : "s"} can be lost and the vault still opens (N − K).
              </div>
              {feedback.errors.map((m) => <Alert key={m} kind="error">{m}</Alert>)}
              {feedback.warnings.map((m) => <Alert key={m} kind="warning">{m}</Alert>)}
              <Field label="Check-in schedule">
                <select aria-label="Schedule" className={inputClass} value={preset} onChange={(e) => setPreset(e.target.value)}>
                  {PRESETS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
                  <option value="custom">Custom (minutes)</option>
                </select>
              </Field>
              {preset === "custom" && (
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Interval (min)">
                    <input className={inputClass} type="number" min={1} value={custom.interval} onChange={(e) => setCustom({ ...custom, interval: Number(e.target.value) })} />
                  </Field>
                  <Field label="Grace (min)">
                    <input className={inputClass} type="number" min={0} value={custom.grace} onChange={(e) => setCustom({ ...custom, grace: Number(e.target.value) })} />
                  </Field>
                </div>
              )}
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Check in every {formatDuration(schedule.interval)}; a missed check-in leads to Warning, then Grace, and release{" "}
                {formatDuration(schedule.grace)} after the deadline.
              </p>
            </div>
          </div>
          <div className="mt-6">
            <Button onClick={create} busy={busy} disabled={feedback.errors.length > 0 || validEmails.length !== emails.filter((e) => e.trim()).length}>
              Create vault &amp; invite trustees
            </Button>
          </div>
        </Card>
      )}

      {step === "invite" && vault && (
        <Card title="Trustee enrolment" subtitle="Send each trustee their link. Their browser generates a keypair; the private key stays with them.">
          <ul className="space-y-3">
            {vault.trustees.map((t) => {
              const invite = invites[t.id];
              return (
                <li key={t.id} className="rounded-xl p-3 ring-1 ring-slate-200 dark:ring-slate-700" data-testid={`invite-${t.position}`}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm font-medium">#{t.position} {t.email}</span>
                    <span className={`text-sm font-semibold ${t.enrolled ? "text-emerald-700 dark:text-emerald-400" : "text-amber-700 dark:text-amber-400"}`}>
                      {t.enrolled ? "✓ enrolled" : "waiting…"}
                    </span>
                  </div>
                  {!t.enrolled && (
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      {invite ? (
                        <>
                          <code className="break-all rounded bg-slate-100 dark:bg-slate-800 px-2 py-1 text-xs" data-testid="invite-link">{invite.link}</code>
                          <CopyButton text={invite.link} />
                        </>
                      ) : (
                        <Button variant="secondary" onClick={() => reissue(t.id)}>Generate a new invite link</Button>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
          <div className="mt-6">
            <Button disabled={!vault.all_enrolled} onClick={() => setStep("secret")}>
              {vault.all_enrolled ? "Next: write your secret" : "Waiting for every trustee to enrol"}
            </Button>
          </div>
        </Card>
      )}

      {step === "secret" && (
        <Card title="Your secret" subtitle="Encrypted in this browser before upload. It is never stored unencrypted anywhere.">
          <div className="space-y-4">
            <Field label="Message">
              <textarea aria-label="Secret message" className={`${inputClass} min-h-40`} value={message} onChange={(e) => setMessage(e.target.value)} />
            </Field>
            <Field label="Attach a file (optional, up to 1 MB)">
              <input aria-label="Attach a file" type="file" className="text-sm" onChange={(e) => void pickFile(e.target.files)} />
            </Field>
            <Button disabled={!message.trim() && !file} onClick={() => setStep("review")}>Review</Button>
          </div>
        </Card>
      )}

      {step === "review" && vault && (
        <Card title="Review and seal" subtitle="Nothing has left your browser yet.">
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div><dt className="text-slate-500 dark:text-slate-400">Threshold</dt><dd className="font-semibold">{vault.k} of {vault.n} trustees ({vault.loss_tolerance} can be lost)</dd></div>
            <div><dt className="text-slate-500 dark:text-slate-400">Schedule</dt><dd className="font-semibold">every {formatDuration(vault.interval_s)}, {formatDuration(vault.grace_s)} grace</dd></div>
            <div><dt className="text-slate-500 dark:text-slate-400">Message</dt><dd className="font-semibold">{message.length} characters</dd></div>
            <div><dt className="text-slate-500 dark:text-slate-400">File</dt><dd className="font-semibold">{file ? `${file.name} (${file.bytes.length} bytes)` : "none"}</dd></div>
          </dl>
          <Alert kind="info">
            On upload, your browser will: generate a 256-bit key → encrypt with AES-256-GCM → split the key into {vault.n} Shamir
            shares (any {vault.k} rebuild it) → encrypt each share to its trustee's public key → send only ciphertext.
          </Alert>
          <div className="mt-4 flex gap-3">
            <Button variant="secondary" onClick={() => setStep("secret")}>Back</Button>
            <Button onClick={encryptAndUpload} busy={busy} data-testid="seal-button">Encrypt &amp; upload</Button>
          </div>
        </Card>
      )}

      {step === "done" && sent && serverView && (
        <div className="space-y-6">
          <Alert kind="success">Sealed. Your vault is now <strong>Active</strong> and the check-in clock is running.</Alert>
          <div className="grid gap-6 lg:grid-cols-2">
            <Card title="What the server received" subtitle="The exact request body (long values truncated).">
              <Mono>{JSON.stringify(truncate(sent), null, 2)}</Mono>
            </Card>
            <Card title="What the server stores" subtitle={`Never received: ${serverView.never_received.join(", ")}.`}>
              <Mono>{JSON.stringify(serverView, null, 2)}</Mono>
            </Card>
          </div>
          <Link to="/dashboard" className="inline-flex rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
            Go to dashboard
          </Link>
        </div>
      )}
    </div>
  );
}
