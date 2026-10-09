/**
 * Trustee private keys live only on the trustee's device (FR-4): in IndexedDB on
 * this browser (optional) and in a downloaded key file the trustee keeps safe.
 */

export const KEY_FILE_FORMAT = "aegis-trustee-key/v1";

export interface TrusteeKeyFile {
  format: typeof KEY_FILE_FORMAT;
  vault_id: string;
  position: number;
  email: string;
  created_at: string;
  private_jwk: JsonWebKey;
}

const DB = "aegis";
const STORE = "trustee-keys";

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

const keyId = (vaultId: string, position: number) => `${vaultId}:${position}`;

export async function rememberKey(file: TrusteeKeyFile): Promise<void> {
  const db = await open();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(file, keyId(file.vault_id, file.position));
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function recallKey(vaultId: string, position: number): Promise<TrusteeKeyFile | null> {
  try {
    const db = await open();
    return await new Promise((resolve, reject) => {
      const req = db.transaction(STORE).objectStore(STORE).get(keyId(vaultId, position));
      req.onsuccess = () => resolve((req.result as TrusteeKeyFile) ?? null);
      req.onerror = () => reject(req.error);
    });
  } catch {
    return null;
  }
}

export function parseKeyFile(text: string): TrusteeKeyFile {
  const data = JSON.parse(text);
  if (data?.format !== KEY_FILE_FORMAT || !data.private_jwk?.d) {
    throw new Error("This is not an Aegis trustee key file.");
  }
  return data as TrusteeKeyFile;
}

export function downloadText(filename: string, text: string, type = "application/json"): void {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Trustee links this browser has seen, so the portal can find them again. */
export function rememberTrusteeToken(token: string): void {
  const tokens = new Set<string>(JSON.parse(localStorage.getItem("aegis.trusteeTokens") ?? "[]"));
  tokens.add(token);
  localStorage.setItem("aegis.trusteeTokens", JSON.stringify([...tokens]));
}

export function knownTrusteeTokens(): string[] {
  return JSON.parse(localStorage.getItem("aegis.trusteeTokens") ?? "[]");
}
