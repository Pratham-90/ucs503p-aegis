/** AES-256-GCM via Web Crypto (FR-2, NFR-SEC-1). Output layout: ciphertext || 16-byte tag. */

export const IV_BYTES = 12;

const encoder = new TextEncoder();

/** Binds a ciphertext to its vault, so blobs/ciphertexts cannot be swapped between vaults. */
export function vaultAad(vaultId: string): Uint8Array {
  return encoder.encode(`aegis-vault:v1:${vaultId}`);
}

function importKey(key: Uint8Array, usage: KeyUsage): Promise<CryptoKey> {
  return crypto.subtle.importKey("raw", key as BufferSource, { name: "AES-GCM" }, false, [usage]);
}

export function randomBytes(length: number): Uint8Array {
  return crypto.getRandomValues(new Uint8Array(length));
}

export async function aesGcmEncrypt(
  key: Uint8Array,
  iv: Uint8Array,
  plaintext: Uint8Array,
  aad: Uint8Array,
): Promise<Uint8Array> {
  const k = await importKey(key, "encrypt");
  const out = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: iv as BufferSource, additionalData: aad as BufferSource, tagLength: 128 },
    k,
    plaintext as BufferSource,
  );
  return new Uint8Array(out);
}

/** Throws (OperationError) if the key, IV, AAD or ciphertext is wrong — GCM authenticates. */
export async function aesGcmDecrypt(
  key: Uint8Array,
  iv: Uint8Array,
  ciphertext: Uint8Array,
  aad: Uint8Array,
): Promise<Uint8Array> {
  const k = await importKey(key, "decrypt");
  const out = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: iv as BufferSource, additionalData: aad as BufferSource, tagLength: 128 },
    k,
    ciphertext as BufferSource,
  );
  return new Uint8Array(out);
}
