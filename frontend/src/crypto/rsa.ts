/**
 * Trustee keypairs and share wrapping: RSA-OAEP, 2048-bit, SHA-256 (FR-2a, FR-4, FR-8).
 * A 68-byte share fits RSA-OAEP-SHA-256's 190-byte limit; the output is 256 bytes.
 */

const ALGORITHM: RsaHashedKeyGenParams = {
  name: "RSA-OAEP",
  modulusLength: 2048,
  publicExponent: new Uint8Array([1, 0, 1]),
  hash: "SHA-256",
};
const IMPORT = { name: "RSA-OAEP", hash: "SHA-256" } as const;

export interface TrusteeKeyPair {
  publicJwk: JsonWebKey;
  privateJwk: JsonWebKey;
}

/** Generated in the trustee's browser; the private key never leaves the device (FR-4). */
export async function generateTrusteeKeyPair(): Promise<TrusteeKeyPair> {
  const pair = (await crypto.subtle.generateKey(ALGORITHM, true, ["encrypt", "decrypt"])) as CryptoKeyPair;
  const publicJwk = await crypto.subtle.exportKey("jwk", pair.publicKey);
  const privateJwk = await crypto.subtle.exportKey("jwk", pair.privateKey);
  return { publicJwk, privateJwk };
}

export function publicPart(jwk: JsonWebKey): JsonWebKey {
  return { kty: jwk.kty, n: jwk.n, e: jwk.e, alg: "RSA-OAEP-256", ext: true, key_ops: ["encrypt"] };
}

export async function wrapForTrustee(publicJwk: JsonWebKey, data: Uint8Array): Promise<Uint8Array> {
  const key = await crypto.subtle.importKey("jwk", publicPart(publicJwk), IMPORT, false, ["encrypt"]);
  return new Uint8Array(await crypto.subtle.encrypt({ name: "RSA-OAEP" }, key, data as BufferSource));
}

export async function unwrapWithPrivateKey(privateJwk: JsonWebKey, data: Uint8Array): Promise<Uint8Array> {
  const jwk = { ...privateJwk, key_ops: ["decrypt"], alg: "RSA-OAEP-256" };
  const key = await crypto.subtle.importKey("jwk", jwk, IMPORT, false, ["decrypt"]);
  return new Uint8Array(await crypto.subtle.decrypt({ name: "RSA-OAEP" }, key, data as BufferSource));
}
