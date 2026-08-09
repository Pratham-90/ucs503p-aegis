# `spikes/` — throwaway feasibility experiments

**Not production code.** Everything here is a quick experiment to de-risk a
design question. It is deliberately un-hardened and must not be imported by the
application. Production code lives in the module packages (`code/crypto`, …).

## `shamir_spike.py` — Shamir's Secret Sharing

Run it:

```bash
python code/spikes/shamir_spike.py
```

### What it proves

- A **hand-written** Shamir scheme over a finite field GF(2^521 − 1) can
  **split** a 256-bit symmetric key into `N` shares and **reconstruct** it from
  **any `K`** shares (verified against two different `K`-subsets), using only
  polynomial evaluation (Horner) and Lagrange interpolation at `x = 0`.
- **`K−1` shares are insufficient** — interpolating fewer than `K` points does
  not recover the secret. This is the threshold property Aegis depends on
  (`NFR-SEC-2`), and it validates the algorithmic core of the whole project:
  the key can be safely fragmented across trustees.
- Modular inverse via `pow(x, -1, p)` (Python 3.8+) and a Mersenne-prime field
  are enough to make the arithmetic correct and dependency-free.

**Conclusion:** the approach is feasible; nothing blocks building the real
`crypto` module on this foundation.

### Hardening required in Week 4 (production `code/crypto`)

The spike cuts corners that the production implementation must fix:

1. **Field & encoding.** Fix a well-specified field and a canonical, versioned
   share serialisation (byte format, not `hex(...)[:34]` display truncation).
   Decide GF(2^8)-per-byte vs a single large prime field for a full key.
2. **Randomness.** `secrets.randbelow` is CSPRNG-backed (good), but coefficient
   generation, edge cases (`k = 1`, `k = n`), and zero-secret handling need
   explicit tests.
3. **Constant-time arithmetic.** Interpolation should avoid secret-dependent
   timing/branching to resist side-channel leakage.
4. **Share integrity & authenticity.** Add a MAC/commitment (or verifiable
   secret sharing) so a tampered or forged share is detected rather than
   silently corrupting the reconstructed key.
5. **Payload encryption.** Pair the recovered key with authenticated encryption
   (e.g. AES-GCM) for the payload — the spike only handles the key, not the
   ciphertext (`NFR-SEC-1`).
6. **Test coverage.** Property-based tests for the `K`-of-`N` guarantee and the
   `K−1` secrecy guarantee, targeting `NFR-MAINT-1` (≥80% on `crypto`).
