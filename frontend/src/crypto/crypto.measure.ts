/**
 * Crypto timing harness (brief section 8). Run with `npm run measure`.
 * Writes metrics/raw/crypto-timing.json; scripts/collect_metrics.py folds it into
 * metrics/prototype-metrics.json. Measured with Node's Web Crypto (labelled so).
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { it } from "vitest";
import { aesGcmDecrypt, aesGcmEncrypt, randomBytes, vaultAad } from "./aes";
import { generateTrusteeKeyPair, wrapForTrustee } from "./rsa";
import { reconstructSecret, splitSecret } from "./shamir";

interface Stat { iterations: number; mean_ms: number; median_ms: number; p95_ms: number }

async function time(iterations: number, fn: () => unknown | Promise<unknown>): Promise<Stat> {
  for (let i = 0; i < Math.min(5, iterations); i++) await fn(); // warm-up
  const samples: number[] = [];
  for (let i = 0; i < iterations; i++) {
    const t0 = performance.now();
    await fn();
    samples.push(performance.now() - t0);
  }
  samples.sort((a, b) => a - b);
  const round = (v: number) => Math.round(v * 1000) / 1000;
  return {
    iterations,
    mean_ms: round(samples.reduce((a, b) => a + b, 0) / iterations),
    median_ms: round(samples[Math.floor(iterations / 2)]),
    p95_ms: round(samples[Math.min(iterations - 1, Math.floor(iterations * 0.95))]),
  };
}

it("measures client crypto timings", async () => {
  const key = randomBytes(32);
  const iv = randomBytes(12);
  const aad = vaultAad("timing");
  const oneMiB = randomBytes(1_048_576);
  const ciphertext = await aesGcmEncrypt(key, iv, oneMiB, aad);
  const secret = BigInt("0x" + "ab".repeat(32));
  const pair = await generateTrusteeKeyPair();
  const shareBytes = randomBytes(68);

  const results: Record<string, Stat> = {
    "aes_gcm_encrypt_1MiB": await time(30, () => aesGcmEncrypt(key, iv, oneMiB, aad)),
    "aes_gcm_decrypt_1MiB": await time(30, () => aesGcmDecrypt(key, iv, ciphertext, aad)),
    "rsa_oaep_wrap_one_share": await time(200, () => wrapForTrustee(pair.publicJwk, shareBytes)),
    "rsa_oaep_2048_keygen": await time(10, () => generateTrusteeKeyPair()),
  };
  for (const [k, n] of [[2, 3], [3, 5], [5, 7]]) {
    const shares = splitSecret(secret, n, k);
    results[`shamir_split_k${k}_n${n}`] = await time(300, () => splitSecret(secret, n, k));
    results[`shamir_reconstruct_k${k}_n${n}`] = await time(300, () => reconstructSecret(shares.slice(0, k)));
  }

  const out = new URL("../../../metrics/raw/crypto-timing.json", import.meta.url);
  mkdirSync(new URL(".", out), { recursive: true });
  writeFileSync(
    out,
    JSON.stringify(
      { environment: `Node.js ${process.version} Web Crypto (${process.platform}/${process.arch})`, measured_at: new Date().toISOString(), results },
      null,
      2,
    ) + "\n",
  );
});
