/** The full client flow in TypeScript: seal -> unwrap -> recover (FR-2, FR-2a, FR-8, NFR-SEC-2). */
import { describe, expect, it } from "vitest";
import { ShamirError, shareFromText, shareToText } from "./encoding";
import { generateTrusteeKeyPair } from "./rsa";
import { reconstructSecret, splitSecret, splitWithCoefficients, validateThreshold } from "./shamir";
import { decryptMyShare, parseShares, recoverVault, RecoveryError, sealVault } from "./vault";

async function sealed(k: number, n: number) {
  const pairs = await Promise.all(Array.from({ length: n }, () => generateTrusteeKeyPair()));
  const trustees = pairs.map((p, i) => ({ id: `t${i + 1}`, position: i + 1, publicJwk: p.publicJwk }));
  const file = { name: "will.txt", type: "text/plain", bytes: new TextEncoder().encode("file body") };
  const payload = await sealVault({ vaultId: "vault-x", k, message: "open me", file, trustees });
  const shares = await Promise.all(
    payload.blobs.map((b, i) => decryptMyShare(pairs[i].privateJwk, b.encrypted_share_b64)),
  );
  return { payload, shares, pairs };
}

describe("client flow", () => {
  it("any K of N trustees recover the message and the file", async () => {
    const { payload, shares } = await sealed(2, 3);
    for (const subset of [[0, 1], [0, 2], [1, 2], [0, 1, 2]]) {
      const result = await recoverVault({
        vaultId: "vault-x", k: 2, ivB64: payload.iv_b64, ciphertextB64: payload.ciphertext_b64,
        shares: subset.map((i) => shares[i]),
      });
      expect(result.message).toBe("open me");
      expect(new TextDecoder().decode(result.file!.bytes)).toBe("file body");
    }
  });

  it("one share alone fails with a clear message", async () => {
    const { payload, shares } = await sealed(2, 3);
    const attempt = recoverVault({ vaultId: "vault-x", k: 2, ivB64: payload.iv_b64,
      ciphertextB64: payload.ciphertext_b64, shares: [shares[0]] });
    await expect(attempt).rejects.toMatchObject({ code: "not_enough_shares" });
  });

  it("K-1 shares fail for K = 3 (reconstruction gives a wrong value)", async () => {
    const { payload, shares } = await sealed(3, 4);
    const attempt = recoverVault({ vaultId: "vault-x", k: 3, ivB64: payload.iv_b64,
      ciphertextB64: payload.ciphertext_b64, shares: shares.slice(0, 2) });
    await expect(attempt).rejects.toBeInstanceOf(RecoveryError);
  });

  it("a ciphertext cannot be opened as another vault's (AAD binding)", async () => {
    const { payload, shares } = await sealed(2, 2);
    const attempt = recoverVault({ vaultId: "other", k: 2, ivB64: payload.iv_b64,
      ciphertextB64: payload.ciphertext_b64, shares });
    await expect(attempt).rejects.toMatchObject({ code: "authentication_failed" });
  });

  it("a wrong private key cannot decrypt someone else's blob", async () => {
    const { payload, pairs } = await sealed(2, 2);
    await expect(decryptMyShare(pairs[1].privateJwk, payload.blobs[0].encrypted_share_b64)).rejects.toThrow(
      /right key file/,
    );
  });

  it("blobs are 256-byte RSA blocks and the request carries no plaintext", async () => {
    const { payload } = await sealed(2, 3);
    expect(atob(payload.blobs[0].encrypted_share_b64).length).toBe(256);
    expect(JSON.stringify(payload)).not.toContain("open me");
  });

  it("validates thresholds like the Python oracle (FR-4)", () => {
    expect(() => validateThreshold(1, 3)).toThrow(/at least 2/);
    expect(() => validateThreshold(4, 3)).toThrow(ShamirError);
    expect(() => splitSecret(5n, 3, 1)).toThrow(ShamirError);
  });

  it("share text round-trips and parsing errors are reported per share", () => {
    const [s] = splitWithCoefficients([7n, 9n], 2);
    expect(shareFromText(shareToText(s))).toEqual(s);
    expect(() => parseShares(["aegis-share:v1:1:@@"])).toThrow(/Share 1/);
    expect(() => reconstructSecret([s, s])).toThrow(/distinct/);
  });
});
