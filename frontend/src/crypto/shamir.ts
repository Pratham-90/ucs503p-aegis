/**
 * Shamir's Secret Sharing over GF(2^521 - 1) with BigInt — the deployed
 * implementation (FR-2a, FR-8). It must reproduce every vector emitted by the
 * authoritative Python module (code/crypto/shamir.py); see vectors.test.ts.
 */

import { FIELD_BYTES, makeShare, MAX_SHARES, PRIME, ShamirError, type Share } from "./encoding";

export { PRIME, type Share };
export const MIN_THRESHOLD = 2; // FR-4: a single trustee must never suffice

/** Returns a uniform field element in [0, p). Injectable for deterministic tests. */
export type RandomFieldElement = () => bigint;

function mod(a: bigint): bigint {
  const r = a % PRIME;
  return r < 0n ? r + PRIME : r;
}

function modPow(base: bigint, exponent: bigint): bigint {
  let result = 1n;
  let b = mod(base);
  let e = exponent;
  while (e > 0n) {
    if (e & 1n) result = (result * b) % PRIME;
    b = (b * b) % PRIME;
    e >>= 1n;
  }
  return result;
}

/** Inverse by Fermat's little theorem (p is prime). */
function modInverse(a: bigint): bigint {
  if (mod(a) === 0n) throw new ShamirError("no inverse of zero");
  return modPow(a, PRIME - 2n);
}

export function validateThreshold(k: number, n: number): void {
  if (!Number.isInteger(k) || !Number.isInteger(n)) throw new ShamirError("K and N must be integers");
  if (k < MIN_THRESHOLD) throw new ShamirError(`threshold K must be at least ${MIN_THRESHOLD} (FR-4), got ${k}`);
  if (n < k) throw new ShamirError(`N must be at least K, got K=${k}, N=${n}`);
  if (n > MAX_SHARES) throw new ShamirError(`N must be at most ${MAX_SHARES}, got ${n}`);
}

function checkFieldElement(v: bigint, what: string): void {
  if (typeof v !== "bigint" || v < 0n || v >= PRIME) throw new ShamirError(`${what} must be an integer in [0, p)`);
}

export function evalPoly(coefficients: readonly bigint[], x: number): bigint {
  const bx = BigInt(x);
  let acc = 0n;
  for (let i = coefficients.length - 1; i >= 0; i--) acc = (acc * bx + coefficients[i]) % PRIME;
  return acc;
}

/** Deterministic split for a given coefficient vector [secret, a1, ..., a(k-1)]. */
export function splitWithCoefficients(coefficients: readonly bigint[], n: number): Share[] {
  validateThreshold(coefficients.length, n);
  coefficients.forEach((c, i) => checkFieldElement(c, i === 0 ? "the secret" : `coefficient a${i}`));
  return Array.from({ length: n }, (_, i) => makeShare(i + 1, evalPoly(coefficients, i + 1)));
}

/** CSPRNG field element by rejection sampling over 521 random bits. */
export const randomFieldElement: RandomFieldElement = () => {
  for (;;) {
    const bytes = crypto.getRandomValues(new Uint8Array(FIELD_BYTES));
    bytes[0] &= 0x01; // keep 521 bits: 1 + 65 * 8
    let v = 0n;
    for (const b of bytes) v = (v << 8n) | BigInt(b);
    if (v < PRIME) return v;
  }
};

export function splitSecret(secret: bigint, n: number, k: number, random: RandomFieldElement = randomFieldElement): Share[] {
  validateThreshold(k, n);
  checkFieldElement(secret, "the secret");
  const coefficients = [secret];
  for (let i = 1; i < k; i++) coefficients.push(random());
  return splitWithCoefficients(coefficients, n);
}

function validatedPoints(shares: readonly Share[]): readonly Share[] {
  const xs = shares.map((s) => s.x);
  if (new Set(xs).size !== xs.length) throw new ShamirError("shares must have distinct x-coordinates");
  shares.forEach((s) => makeShare(s.x, s.y));
  return shares;
}

export function interpolateAt(shares: readonly Share[], x: number): bigint {
  const points = validatedPoints(shares);
  if (points.length === 0) throw new ShamirError("at least one share is required");
  const bx = BigInt(x);
  let total = 0n;
  for (let i = 0; i < points.length; i++) {
    let num = 1n;
    let den = 1n;
    for (let j = 0; j < points.length; j++) {
      if (i === j) continue;
      num = mod(num * (bx - BigInt(points[j].x)));
      den = mod(den * BigInt(points[i].x - points[j].x));
    }
    total = mod(total + points[i].y * num * modInverse(den));
  }
  return total;
}

/** Recover f(0). With fewer than K shares the result is an unrelated value (the threshold property). */
export function reconstructSecret(shares: readonly Share[]): bigint {
  const points = validatedPoints(shares);
  if (points.length < MIN_THRESHOLD) throw new ShamirError(`at least ${MIN_THRESHOLD} shares are required`);
  return interpolateAt(points, 0);
}
