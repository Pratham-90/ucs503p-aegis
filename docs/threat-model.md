# Threat model

This document analyses the adversaries Aegis v1 is designed against, and — just
as importantly — the ones it is **not**. It follows directly from the
[Trust model](srs/index.md#23-trust-model): the server is trusted for
scheduling and availability, **never for confidentiality**. Mitigations cite the
functional (`FR-*`) and non-functional (`NFR-*`) requirements in the
[SRS](srs/index.md) that carry them.

Threats that are **not fully mitigated in v1** are marked as such in the table
and collected in [Residual risks](#residual-risks). They are stated plainly
rather than written as if solved.

## Assets being protected

- **Payload confidentiality** — the plaintext files/messages must be readable
  only by `≥ K` cooperating trustees after a legitimate release.
- **Temporal safety** — no disclosure before `deadline + grace` (`NFR-REL-1`);
  premature release is irreversible and is the catastrophic failure mode.
- **Release availability** — a legitimate release should eventually happen when
  the Owner is truly absent.

## Threats

| ID | Threat | Attacker capability | Impact | Mitigation | Covered by | Status |
| --- | --- | --- | --- | --- | --- | --- |
| **T-1** | Malicious single trustee | Controls one trustee account + device; decrypts their own blob to one plaintext share | **None alone** — one share is below threshold and reveals nothing about the key (information-theoretic) | Shamir threshold: any `≤ K−1` shares reveal nothing | `FR-2a`, `FR-4`, `NFR-SEC-2` | Mitigated (for `K ≥ 2`) |
| **T-2** | Colluding trustees (`≥ K`) | `K` or more trustees pool their decrypted shares | **Full payload disclosure** | **Partial only.** This *is* the intended recovery path, so it cannot be prevented cryptographically; a larger `K` only raises the bar | `FR-4` (choice of `K`); `NFR-SEC-2` bounds only `< K` | **Not mitigated for `≥ K` (by design)** |
| **T-3** | Server compromise (passive / storage exfiltration) | Reads everything at rest: ciphertext payload, `N` trustee-encrypted blobs, metadata, backups | **Cannot decrypt** — all payload material is ciphertext or encrypted to trustees' public keys; would additionally need `≥ K` trustee private keys | Zero-knowledge storage: client-side crypto, per-trustee public-key share encryption | `FR-2`, `FR-2a`, `NFR-SEC-1`, `NFR-SEC-5` | Mitigated (payload); **metadata leaks — see T-3 residual** |
| **T-4** | Malicious operator / active server (incl. backdoored client code) | Full control of the running server: read storage, alter responses, **serve modified client JavaScript**, control release timing | Cannot read *existing* payloads from storage (as T-3), **but** can serve backdoored client code that exfiltrates the key/plaintext at encryption or reconstruction time → *future* payloads compromised; can also force early blob release | **Partial.** Zero-knowledge holds against passive/storage compromise, **not** against code-delivery tampering. TLS (`NFR-SEC-4`) protects transit only | `NFR-SEC-4` (transit); otherwise residual | **Code-delivery vector NOT mitigated in v1** |
| **T-5** | Check-in token replay | Captures a one-action check-in token (from email, logs, or network) and re-submits it | A replayed token falsely confirms a check-in, **delaying/suppressing** a legitimate release (fails *sealed*). Does **not** cause early release or disclosure | Tokens are single-use, expiring, and bound to the specific check-in period; invalidated on use or period end | `FR-6`, `NFR-USE-1` | Mitigated (single replay); sustained suppression → residual |
| **T-6** | Premature release from clock skew or restart | Fault, not adversary: forward clock jump, NTP misconfig, or a restart recomputing deadlines wrongly | **Catastrophic** if it triggers early, irreversible disclosure | Absolute persisted deadlines re-armed on restart, never fired early; reliability suite of `≥ 1000` schedules incl. clock jumps and restarts proving **zero** early releases | `NFR-REL-1`, `NFR-REL-2`, `NFR-REL-3` | Mitigated (spec + suite); depends on implementation |
| **T-7** | Denial of release by the server | Server (buggy or malicious operator) stops the scheduler, withholds blobs, or deletes data | **Legitimate release never happens** — Owner's intent defeated (availability failure, not confidentiality) | **Limited.** The server is trusted for availability by design; no cryptographic defense in v1 | Trust-model boundary; `NFR-REL-*` ensure *not-early*, not *not-never* | **Not mitigated in v1 (accepted)** |
| **T-8** | Trustee email / account compromise | Controls a trustee's inbox; receives the release notification and blob | Obtains that trustee's **encrypted** blob — useless without the private key (on the trustee's device). One email ≠ one share; disclosure needs `≥ K` trustee *private keys* | Shares encrypted under trustee public keys; private keys never leave devices | `FR-2a`, `FR-4`, `NFR-SEC-5` | Mitigated (email alone); device compromise → one share |
| **T-9** | Payload / blob tampering by the server (integrity) | Alters stored ciphertext or blobs | Reconstruction fails or yields garbage → **denial**, not disclosure (with AEAD, tampering is detected) | **Partial.** Authenticated encryption (AEAD) for the payload is planned; verifiable/authenticated shares (VSS) are **deferred to Week 4** | `NFR-SEC-1` (partial); future crypto hardening | **Share integrity NOT in v1** |

## Residual risks

The following are **not fully mitigated in v1** and are accepted, deferred, or
inherent. They must be weighed before the system is relied upon:

1. **Collusion of `≥ K` trustees (T-2).** Inherent to threshold secret sharing —
   this is the recovery mechanism. Mitigated only by choosing `K` sensibly
   relative to how much the trustees are trusted.
2. **Malicious server serving backdoored client code (T-4).** The central caveat
   to the "zero-knowledge" claim in a web-delivered application: the server ships
   the crypto code, so a compromised/dishonest server can subvert it at the
   source. v1 has **no** mitigation. Future options: subresource-integrity
   pinning to a trusted origin, reproducible and signed client builds, an
   out-of-band client (browser extension / desktop app), or third-party code
   audit of a pinned bundle.
3. **Denial of release by the server (T-7).** The server is a single point of
   availability for release. No v1 mitigation. Future: an external watchdog,
   redundancy, or a trustee-initiated recovery path independent of the operator.
4. **Metadata confidentiality (T-3).** Filenames, sizes, MIME types, trustee
   email addresses, and the check-in schedule are stored **unencrypted** and
   leak on server compromise. Only the payload and shares are protected.
5. **Configuration foot-guns.** `K = 1` lets any single trustee open the vault
   (defeating distributed trust); `K = N` makes one lost or unreachable trustee
   fatal to recovery. v1 does not yet enforce sane defaults or warn on these.
6. **Recovery availability.** If more than `N − K` trustees lose their private
   keys or become unreachable, the vault is **permanently unrecoverable** — the
   unavoidable flip side of requiring `K` cooperating parties.
7. **Share integrity (T-9).** Verifiable secret sharing / share authentication
   is deferred to Week 4; until then a tampered share can silently corrupt a
   reconstruction rather than being rejected.
8. **Sustained check-in suppression (T-5 + T-8).** An attacker with ongoing
   control of the Owner's email could keep confirming check-ins to suppress a
   legitimate release indefinitely.

## Summary of the guarantee

Aegis v1 guarantees that **the server alone can never read a payload**: a
confidentiality breach requires the server **and** at least `K` trustees. It
does **not** guarantee availability of release against a hostile operator, nor
does it defend against a server that tampers with the client code it serves.
Those boundaries are deliberate and are restated wherever the guarantee is
claimed.
