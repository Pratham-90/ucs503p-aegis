import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorMessage } from "../api";
import { Alert, Button, Card } from "../components/ui";
import { generateTrusteeKeyPair, publicPart } from "../crypto/rsa";
import { downloadText, KEY_FILE_FORMAT, rememberKey, rememberTrusteeToken, type TrusteeKeyFile } from "../keystore";

interface InviteInfo {
  vault_id: string;
  trustee_email: string;
  owner_email: string;
  position: number;
  enrolled: boolean;
  k: number;
  n: number;
  can_enrol: boolean;
}

/** FR-4: the keypair is generated here, in the trustee's browser. Only the public key is uploaded. */
export function TrusteeEnrol() {
  const { token = "" } = useParams();
  const [info, setInfo] = useState<InviteInfo | null>(null);
  const [keyFile, setKeyFile] = useState<TrusteeKeyFile | null>(null);
  const [remember, setRemember] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<InviteInfo>(`/trustee/invite/${token}`).then(setInfo).catch((e) => setError(errorMessage(e)));
  }, [token]);

  const fileName = (f: TrusteeKeyFile) => `aegis-trustee-${f.email}.json`;

  async function enrol() {
    if (!info) return;
    setBusy(true);
    setError(null);
    try {
      const { publicJwk, privateJwk } = await generateTrusteeKeyPair();
      await api.post(`/trustee/enrol/${token}`, { public_key_jwk: publicPart(publicJwk) });
      const file: TrusteeKeyFile = {
        format: KEY_FILE_FORMAT,
        vault_id: info.vault_id,
        position: info.position,
        email: info.trustee_email,
        created_at: new Date().toISOString(),
        private_jwk: privateJwk,
      };
      downloadText(fileName(file), JSON.stringify(file, null, 2)); // forced download: the trustee's copy
      if (remember) await rememberKey(file);
      rememberTrusteeToken(token);
      setKeyFile(file);
      setInfo({ ...info, enrolled: true, can_enrol: true });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Card title="Trustee enrolment" subtitle={info ? `${info.owner_email} named you trustee #${info.position} of ${info.n}.` : undefined}>
        {error && <Alert kind="error">{error}</Alert>}
        {info && !keyFile && info.enrolled && (
          <Alert kind="success">
            You have already enrolled. Keep your key file safe. <Link className="font-semibold underline" to={`/trustee?t=${token}`}>Open the trustee portal</Link>.
          </Alert>
        )}
        {info && !info.enrolled && !info.can_enrol && <Alert kind="warning">This vault is already sealed; enrolment is closed.</Alert>}
        {info && !info.enrolled && info.can_enrol && (
          <div className="space-y-4 text-sm text-slate-700">
            <p>
              Your browser will now generate an RSA-2048 keypair. Only the <strong>public</strong> key is sent to Aegis; the{" "}
              <strong>private</strong> key is downloaded as a file that only you hold. Without it you cannot help open the vault.
            </p>
            <p>
              The vault opens only if its owner stops checking in <em>and</em> {info.k} of the {info.n} trustees combine their shares.
            </p>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
              Also remember the key in this browser (IndexedDB)
            </label>
            <Button onClick={enrol} busy={busy} data-testid="enrol-button">Generate my keypair &amp; enrol</Button>
          </div>
        )}
        {keyFile && (
          <div className="space-y-4">
            <Alert kind="success">
              Enrolled. Your private key was downloaded as <code>{fileName(keyFile)}</code>. Store it somewhere safe.
            </Alert>
            <div className="flex flex-wrap gap-3">
              <Button variant="secondary" onClick={() => downloadText(fileName(keyFile), JSON.stringify(keyFile, null, 2))}>
                Download key file again
              </Button>
              <Link to={`/trustee?t=${token}`} className="inline-flex rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white">
                Open trustee portal
              </Link>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
