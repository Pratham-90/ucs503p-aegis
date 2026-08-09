# Diagrams

The models that accompany the [SRS](../srs/index.md), authored as Mermaid so
they render on this site and stay diffable in version control.

- **[Use-case diagram](use-case.md)** — actors Owner, Trustee, and the
  time-triggered Scheduler (system actor), mapped to `FR-1`…`FR-8`.
- **[Vault lifecycle](vault-lifecycle.md)** — the Active → Warning → Grace →
  Released state machine, with the release gate that enforces `NFR-REL-1`.
- **[High-level architecture](architecture.md)** — frontend, FastAPI backend,
  the four domain packages, and the persistence/scheduling/email edges.
