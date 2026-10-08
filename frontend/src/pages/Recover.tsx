import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, errorMessage } from "../api";
import { Alert, Button, Card, Field, inputClass } from "../components/ui";
import { parseShares, recoverVault, RecoveryError, type RecoveredPayload } from "../crypto/vault";
import { downloadText } from "../keystore";

interface ReleasedPayload {
  vault_id: string;
  k: number;
  n: number;
  iv_b64: string;
  ciphertext_b64: string;
}

/**
 * The Recovery Room runs entirely in this browser (FR-8): the server only hands
 * over the ciphertext, which is useless without K decrypted shares.
 */
export function Recover() {
  const [params] = useSearchParams();
  const [token, setToken] = useState(params.get("t") ?? "");
  const [payload, setPayload] = useState<ReleasedPayload | null>(null);
  const [shares, setShares] = useState<string[]>(["", ""]);
  const [result, setResult] = useState<RecoveredPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function fetchPayload(t: string) {
    setError(null);
    try {
      const p = await api.get<ReleasedPayload>(`/trustee/payload/${encodeURIComponent(t)}`);
      setPayload(p);
      setShares((prev) => (prev.length < p.k ? [...prev, ...Array(p.k - prev.length).fill("")] : prev));
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  useEffect(() => {
    const t = params.get("t");
    if (t) void fetchPayload(t);
  }, [params]);

  async function addFromFiles(list: FileList | null) {
    if (!list) return;
    const texts = await Promise.all(Array.from(list).map((f) => f.text()));
    setShares((prev) => [...prev.filter((s) => s.trim()), ...texts.map((t) => t.trim())]);
  }

  async function recover() {
    if (!payload) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const parsed = parseShares(shares);
      setResult(
        await recoverVault({ vaultId: payload.vault_id, k: payload.k, ivB64: payload.iv_b64, ciphertextB64: payload.ciphertext_b64, shares: parsed }),
      );
    } catch (e) {
      setError(e instanceof RecoveryError ? e.message : errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const provided = shares.filter((s) => s.trim()).length;
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Recovery Room</h1>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Paste at least K shares. The key is reconstructed and the vault decrypted in this browser — nothing you paste is sent anywhere.
        </p>
      </div>

      {!payload && (
        <Card title="1. Which vault?" subtitle="Use a trustee link (from the portal or the release email).">
          <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); void fetchPayload(token.match(/[?&]t=([^&\s]+)/)?.[1] ?? token.trim()); }}>
            <input aria-label="Trustee link or token" className={`${inputClass} flex-1`} value={token} onChange={(e) => setToken(e.target.value)} />
            <Button type="submit" variant="secondary">Load vault</Button>
          </form>
        </Card>
      )}

      {payload && (
        <Card title={`Shares (${provided} provided, ${payload.k} of ${payload.n} needed)`} subtitle="Format: aegis-share:v1:<x>:<y>">
          <div className="space-y-3">
            {shares.map((value, i) => (
              <Field key={i} label={`Share ${i + 1}`}>
                <textarea
                  aria-label={`Share ${i + 1}`}
                  className={`${inputClass} font-mono text-xs`}
                  rows={2}
                  value={value}
                  onChange={(e) => setShares(shares.map((s, j) => (j === i ? e.target.value : s)))}
                />
              </Field>
            ))}
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="secondary" type="button" onClick={() => setShares([...shares, ""])}>Add a share</Button>
              <label className="text-sm text-slate-600 dark:text-slate-400">
                or upload share files <input aria-label="Share files" type="file" multiple accept=".txt,text/plain" className="ml-2 text-sm" onChange={(e) => void addFromFiles(e.target.files)} />
              </label>
            </div>
            {provided > 0 && provided < payload.k && (
              <Alert kind="warning">Only {provided} share{provided === 1 ? "" : "s"}: fewer than K = {payload.k} reveal nothing, so decryption will fail.</Alert>
            )}
            <Button onClick={recover} busy={busy} disabled={provided === 0} data-testid="recover-button">
              Reconstruct &amp; decrypt
            </Button>
          </div>
        </Card>
      )}

      {error && <Alert kind="error">{error}</Alert>}

      {result && (
        <Card title="Vault opened" subtitle="Decrypted in this browser.">
          <div className="whitespace-pre-wrap rounded-lg bg-emerald-50 dark:bg-emerald-500/10 p-4 text-slate-900 dark:text-slate-100 ring-1 ring-emerald-200 dark:ring-emerald-500/30" data-testid="recovered-message">
            {result.message || <em className="text-slate-500 dark:text-slate-400">(no message)</em>}
          </div>
          {result.file && (
            <Button
              className="mt-4"
              variant="secondary"
              onClick={() => {
                const url = URL.createObjectURL(new Blob([result.file!.bytes as BlobPart], { type: result.file!.type }));
                const a = document.createElement("a");
                a.href = url;
                a.download = result.file!.name;
                a.click();
                setTimeout(() => URL.revokeObjectURL(url), 1000);
              }}
            >
              Download {result.file.name}
            </Button>
          )}
          <Button className="mt-4 ml-2" variant="ghost" onClick={() => downloadText("aegis-message.txt", result.message, "text/plain")}>
            Save message as text
          </Button>
        </Card>
      )}
    </div>
  );
}
