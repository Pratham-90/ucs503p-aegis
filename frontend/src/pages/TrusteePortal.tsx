import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, errorMessage, type VaultState } from "../api";
import { Alert, Button, Card, CopyButton, Field, inputClass, Mono, StateBadge } from "../components/ui";
import { shareToText } from "../crypto/encoding";
import { decryptMyShare } from "../crypto/vault";
import { downloadText, knownTrusteeTokens, parseKeyFile, recallKey, rememberTrusteeToken, type TrusteeKeyFile } from "../keystore";

interface GuardedVault {
  vault_id: string;
  owner_email: string;
  state: VaultState;
  k: number;
  n: number;
  your_position: number;
  your_email: string;
  released_at: string | null;
  blob_available: boolean;
}

function tokenFrom(input: string): string {
  const match = input.match(/[?&]t=([^&\s]+)/) ?? input.match(/\/trustee\/enrol\/([^/?\s]+)/);
  return match ? match[1] : input.trim();
}

function VaultCard({ token, vault }: { token: string; vault: GuardedVault }) {
  const [keyFile, setKeyFile] = useState<TrusteeKeyFile | null>(null);
  const [share, setShare] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void recallKey(vault.vault_id, vault.your_position).then((k) => k && setKeyFile(k));
  }, [vault.vault_id, vault.your_position]);

  async function loadFile(list: FileList | null) {
    const f = list?.[0];
    if (!f) return;
    try {
      setKeyFile(parseKeyFile(await f.text()));
      setError(null);
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function decrypt() {
    if (!keyFile) return;
    setBusy(true);
    setError(null);
    try {
      const blob = await api.get<{ encrypted_share_b64: string }>(`/trustee/blob/${token}`);
      setShare(shareToText(await decryptMyShare(keyFile.private_jwk, blob.encrypted_share_b64)));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card
      title={<span className="flex items-center gap-3">{vault.owner_email}'s vault <StateBadge state={vault.state} /></span>}
      subtitle={`You are trustee #${vault.your_position} (${vault.your_email}). Threshold: ${vault.k} of ${vault.n}.`}
    >
      {!vault.blob_available ? (
        <Alert kind="info">
          Nothing to do. You will be emailed if the owner stops checking in and the grace period ends. Until then the server
          will not release anything (NFR-REL-1).
        </Alert>
      ) : (
        <div className="space-y-4">
          <Alert kind="warning">This vault was released{vault.released_at ? ` at ${new Date(vault.released_at).toLocaleString()}` : ""}.</Alert>
          {keyFile ? (
            <p className="text-sm text-emerald-700">Private key loaded ({keyFile.email}).</p>
          ) : (
            <Field label="Load your private key file (aegis-trustee-….json)">
              <input aria-label="Private key file" type="file" accept=".json,application/json" className="text-sm" onChange={(e) => void loadFile(e.target.files)} />
            </Field>
          )}
          <Button onClick={decrypt} busy={busy} disabled={!keyFile} data-testid="decrypt-share">
            Decrypt my share
          </Button>
          {share && (
            <div className="space-y-2">
              <p className="text-sm text-slate-700">Your share (decrypted in this browser). Give it to the Recovery Room:</p>
              <Mono className="whitespace-pre-wrap break-all" >{share}</Mono>
              <div className="flex flex-wrap gap-2">
                <CopyButton text={share} label="Copy share" />
                <Button variant="secondary" onClick={() => downloadText(`aegis-share-${vault.your_position}.txt`, share, "text/plain")}>
                  Download share
                </Button>
                <Link to={`/recover?t=${token}`} className="inline-flex rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white">
                  Open Recovery Room
                </Link>
              </div>
            </div>
          )}
        </div>
      )}
      {error && <div className="mt-4"><Alert kind="error">{error}</Alert></div>}
    </Card>
  );
}

export function TrusteePortal() {
  const [params] = useSearchParams();
  const [tokens, setTokens] = useState<string[]>(() => {
    const t = params.get("t");
    if (t) rememberTrusteeToken(t);
    return [...new Set([...(t ? [t] : []), ...knownTrusteeTokens()])];
  });
  const [vaults, setVaults] = useState<Record<string, GuardedVault>>({});
  const [errors, setErrors] = useState<string[]>([]);
  const [manual, setManual] = useState("");

  const load = useCallback(async () => {
    const found: Record<string, GuardedVault> = {};
    const errs: string[] = [];
    await Promise.all(
      tokens.map(async (t) => {
        try {
          const { vaults } = await api.get<{ vaults: GuardedVault[] }>(`/trustee/vaults?t=${encodeURIComponent(t)}`);
          for (const v of vaults) if (!Object.values(found).some((f) => f.vault_id === v.vault_id)) found[t] = v;
        } catch (e) {
          errs.push(errorMessage(e));
        }
      }),
    );
    setVaults(found);
    setErrors(errs);
  }, [tokens]);

  useEffect(() => {
    void load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [load]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Trustee portal</h1>
        <p className="text-sm text-slate-600">Vaults you guard, and their state. No secrets are shown here until a vault is released.</p>
      </div>
      {Object.entries(vaults).map(([t, v]) => <VaultCard key={v.vault_id} token={t} vault={v} />)}
      {Object.keys(vaults).length === 0 && <Alert kind="info">No vaults found for this browser yet.</Alert>}
      {errors.map((e) => <Alert key={e} kind="error">{e}</Alert>)}
      <Card title="Open a trustee link" subtitle="Paste the link from your invitation or release email.">
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const t = tokenFrom(manual);
            if (!t) return;
            rememberTrusteeToken(t);
            setTokens((prev) => [...new Set([t, ...prev])]);
            setManual("");
          }}
        >
          <input aria-label="Trustee link" className={`${inputClass} flex-1`} value={manual} onChange={(e) => setManual(e.target.value)} placeholder="https://…/trustee?t=…" />
          <Button type="submit" variant="secondary">Open</Button>
        </form>
      </Card>
    </div>
  );
}
