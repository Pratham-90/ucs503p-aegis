/**
 * Byte/text encodings shared with the authoritative Python crypto
 * (code/crypto/encoding.py). Formats, version 1:
 *   key         32 bytes (AES-256), big-endian integer for Shamir
 *   share bytes 0x01 || x (1 byte) || y (66 bytes, big-endian)  = 68 bytes
 *   share text  aegis-share:v1:<x>:<y base64url, no padding>
 */

export const KEY_BYTES = 32;
export const FIELD_BYTES = 66;
export const SHARE_VERSION = 1;
export const SHARE_BYTES = 2 + FIELD_BYTES;
export const SHARE_TEXT_PREFIX = "aegis-share:v1:";

export class ShamirError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ShamirError";
  }
}

export interface Share {
  x: number;
  y: bigint;
}

/** The 13th Mersenne prime, 2^521 - 1 (same field as the Python implementation). */
export const PRIME = (1n << 521n) - 1n;
export const MAX_SHARES = 255;

/** Validating constructor, mirroring Python's ``Share.__post_init__``. */
export function makeShare(x: number, y: bigint): Share {
  if (!Number.isInteger(x) || x < 1 || x > MAX_SHARES) throw new ShamirError(`share x must be in 1..${MAX_SHARES}`);
  if (typeof y !== "bigint" || y < 0n || y >= PRIME) throw new ShamirError("share y is not an element of the field");
  return { x, y };
}

export function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function hexToBytes(hex: string): Uint8Array {
  if (hex.length % 2 !== 0 || /[^0-9a-f]/i.test(hex)) throw new Error("invalid hex");
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.slice(2 * i, 2 * i + 2), 16);
  return out;
}

export function bytesToB64(bytes: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  }
  return btoa(binary);
}

export function b64ToBytes(b64: string): Uint8Array {
  const binary = atob(b64);
  const out = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) out[i] = binary.charCodeAt(i);
  return out;
}

export function bytesToB64url(bytes: Uint8Array): string {
  return bytesToB64(bytes).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function b64urlToBytes(text: string): Uint8Array {
  if (/[^A-Za-z0-9_-]/.test(text)) throw new Error("not base64url");
  const b64 = text.replace(/-/g, "+").replace(/_/g, "/");
  return b64ToBytes(b64 + "=".repeat((4 - (b64.length % 4)) % 4));
}

export function bigintFromBytes(bytes: Uint8Array): bigint {
  let value = 0n;
  for (const b of bytes) value = (value << 8n) | BigInt(b);
  return value;
}

export function bigintToBytes(value: bigint, length: number): Uint8Array {
  if (value < 0n || value >= 1n << BigInt(8 * length)) throw new ShamirError("value does not fit");
  const out = new Uint8Array(length);
  for (let i = length - 1; i >= 0; i--) {
    out[i] = Number(value & 0xffn);
    value >>= 8n;
  }
  return out;
}

export function keyToBigInt(key: Uint8Array): bigint {
  if (key.length !== KEY_BYTES) throw new ShamirError(`key must be ${KEY_BYTES} bytes`);
  return bigintFromBytes(key);
}

/** A reconstruction from too few (or wrong) shares almost never fits in 256 bits. */
export function bigintToKey(value: bigint): Uint8Array {
  if (value < 0n || value >= 1n << 256n) {
    throw new ShamirError("reconstructed value is not a valid 256-bit key (too few or wrong shares)");
  }
  return bigintToBytes(value, KEY_BYTES);
}

export function shareToBytes(share: Share): Uint8Array {
  const out = new Uint8Array(SHARE_BYTES);
  out[0] = SHARE_VERSION;
  out[1] = share.x;
  out.set(bigintToBytes(share.y, FIELD_BYTES), 2);
  return out;
}

export function shareFromBytes(data: Uint8Array): Share {
  if (data.length !== SHARE_BYTES || data[0] !== SHARE_VERSION) throw new ShamirError("malformed share bytes");
  return makeShare(data[1], bigintFromBytes(data.subarray(2)));
}

export function shareToText(share: Share): string {
  return `${SHARE_TEXT_PREFIX}${share.x}:${bytesToB64url(bigintToBytes(share.y, FIELD_BYTES))}`;
}

export function shareFromText(text: string): Share {
  const trimmed = text.trim();
  if (!trimmed.startsWith(SHARE_TEXT_PREFIX)) throw new ShamirError("share text must start with 'aegis-share:v1:'");
  const parts = trimmed.slice(SHARE_TEXT_PREFIX.length).split(":");
  if (parts.length !== 2 || !/^\d+$/.test(parts[0])) {
    throw new ShamirError("share text must look like aegis-share:v1:<x>:<y>");
  }
  let yBytes: Uint8Array;
  try {
    yBytes = b64urlToBytes(parts[1]);
  } catch {
    throw new ShamirError("share y is not valid base64url");
  }
  if (yBytes.length !== FIELD_BYTES) throw new ShamirError(`share y must decode to ${FIELD_BYTES} bytes`);
  return makeShare(Number(parts[0]), bigintFromBytes(yBytes));
}
