/**
 * The client-side flows of the zero-knowledge design (FR-2, FR-2a, FR-8, NFR-SEC-5):
 *   seal    random key -> AES-GCM(payload) -> Shamir split -> RSA-OAEP wrap per trustee
 *   unwrap  trustee's private key -> their own share
 *   recover >= K shares -> Lagrange at 0 -> key -> AES-GCM decrypt
 * Nothing here ever sends the key, the plaintext or a plaintext share to the server.
 */

import { aesGcmDecrypt, aesGcmEncrypt, IV_BYTES, randomBytes, vaultAad } from "./aes";
import {
  b64ToBytes,
  bigintToKey,
  bytesToB64,
  keyToBigInt,
  ShamirError,
  shareFromBytes,
  shareFromText,
  shareToBytes,
  type Share,
} from "./encoding";
import { unwrapWithPrivateKey, wrapForTrustee } from "./rsa";
import { reconstructSecret, splitSecret } from "./shamir";

export const MAX_FILE_BYTES = 1_048_576; // prototype cap; larger files are future work

export interface FileInput {
  name: string;
  type: string;
  bytes: Uint8Array;
}

export interface TrusteeKeyRef {
  id: string;
  position: number;
  publicJwk: JsonWebKey;
}

export interface SealedPayload {
  ciphertext_b64: string;
  iv_b64: string;
  meta: { v: number; alg: string; size_bytes: number; has_file: boolean };
  blobs: { trustee_id: string; x_index: number; encrypted_share_b64: string }[];
}

const encoder = new TextEncoder();
const decoder = new TextDecoder();

/** Same envelope as Python's pack_payload. File names stay inside the ciphertext. */
export function packPayload(message: string, file?: FileInput | null): Uint8Array {
  const envelope = {
    v: 1,
    message,
    file: file ? { name: file.name, type: file.type, data: bytesToB64(file.bytes) } : null,
  };
  return encoder.encode(JSON.stringify(envelope));
}

export async function sealVault(args: {
  vaultId: string;
  k: number;
  message: string;
  file?: FileInput | null;
  trustees: TrusteeKeyRef[];
}): Promise<SealedPayload> {
  if (args.file && args.file.bytes.length > MAX_FILE_BYTES) throw new Error("files are limited to 1 MB");
  const key = randomBytes(32);
  const iv = randomBytes(IV_BYTES);
  const plaintext = packPayload(args.message, args.file);
  try {
    const ciphertext = await aesGcmEncrypt(key, iv, plaintext, vaultAad(args.vaultId));
    const shares = splitSecret(keyToBigInt(key), args.trustees.length, args.k);
    const blobs = await Promise.all(
      args.trustees.map(async (t) => {
        const share = shares[t.position - 1];
        const wrapped = await wrapForTrustee(t.publicJwk, shareToBytes(share));
        return { trustee_id: t.id, x_index: share.x, encrypted_share_b64: bytesToB64(wrapped) };
      }),
    );
    return {
      ciphertext_b64: bytesToB64(ciphertext),
      iv_b64: bytesToB64(iv),
      meta: { v: 1, alg: "AES-256-GCM", size_bytes: plaintext.length, has_file: !!args.file },
      blobs,
    };
  } finally {
    key.fill(0); // best effort: JS cannot guarantee the key leaves memory
    plaintext.fill(0);
  }
}

export async function decryptMyShare(privateJwk: JsonWebKey, encryptedShareB64: string): Promise<Share> {
  try {
    return shareFromBytes(await unwrapWithPrivateKey(privateJwk, b64ToBytes(encryptedShareB64)));
  } catch (e) {
    if (e instanceof ShamirError) throw e;
    throw new Error("This private key cannot decrypt the share. Did you load the right key file?", { cause: e });
  }
}

export class RecoveryError extends Error {
  constructor(
    public code: "not_enough_shares" | "invalid_share" | "authentication_failed",
    message: string,
  ) {
    super(message);
    this.name = "RecoveryError";
  }
}

export interface RecoveredPayload {
  message: string;
  file: FileInput | null;
}

export function parseShares(texts: string[]): Share[] {
  return texts
    .map((t) => t.trim())
    .filter(Boolean)
    .map((t, i) => {
      try {
        return shareFromText(t);
      } catch (e) {
        throw new RecoveryError("invalid_share", `Share ${i + 1}: ${(e as Error).message}`);
      }
    });
}

export async function recoverVault(args: {
  vaultId: string;
  k: number;
  ivB64: string;
  ciphertextB64: string;
  shares: Share[];
}): Promise<RecoveredPayload> {
  const { shares, k } = args;
  let key: Uint8Array;
  try {
    key = bigintToKey(reconstructSecret(shares));
  } catch (e) {
    const tooFew = shares.length < k;
    throw new RecoveryError(
      tooFew ? "not_enough_shares" : "invalid_share",
      tooFew
        ? `Not enough shares: this vault needs ${k}, you provided ${shares.length}. Fewer than K shares reveal nothing about the key.`
        : `These shares do not reconstruct a valid key (${(e as Error).message}).`,
    );
  }
  try {
    const plaintext = await aesGcmDecrypt(key, b64ToBytes(args.ivB64), b64ToBytes(args.ciphertextB64), vaultAad(args.vaultId));
    const envelope = JSON.parse(decoder.decode(plaintext));
    return {
      message: envelope.message ?? "",
      file: envelope.file
        ? { name: envelope.file.name, type: envelope.file.type, bytes: b64ToBytes(envelope.file.data) }
        : null,
    };
  } catch {
    throw new RecoveryError(
      shares.length < k ? "not_enough_shares" : "authentication_failed",
      shares.length < k
        ? `Not enough shares: this vault needs ${k}, you provided ${shares.length}. AES-GCM authentication failed, as expected.`
        : "Decryption failed authentication: at least one share is wrong or belongs to another vault.",
    );
  } finally {
    key.fill(0);
  }
}
