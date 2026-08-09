![Tiet Logo](assets/tiet-logo.svg){ .tiet-logo }

**UCS503: Software Engineering (Project)**  
**TIET Patiala**

# Aegis — an encrypted "dead man's switch" legacy vault

**Author:** Pratham Arora (Roll No. `1024030001`, COE) — `parora_be24@thapar.edu`

Aegis lets an **Owner** store encrypted files and messages in a **vault** and
designate **trustees** who can open it *only if the Owner stops responding*. The
Owner checks in at a configured interval; miss a check-in, and after a **grace
period** the decryption key — pre-split with **Shamir's Secret Sharing** so that
any **K of N** shares reconstruct it and any **K−1** reveal nothing — is
distributed to the trustees, who together open the vault.

## Documentation map

| Page | What it covers |
| --- | --- |
| [Software Requirements Specification](srs/index.md) | Purpose, scope, non-goals, glossary, functional (`FR-*`) and non-functional (`NFR-*`) requirements, assumptions & constraints. |
| [Diagrams](diagrams/index.md) | Use-case, vault-lifecycle state machine, and high-level architecture. |
| [12-Week Plan](plan/twelve-week-plan.md) | Week-by-week roadmap for the UCS503P timeline. |
| [Project selection criteria](criteria-for-project-selection.md) | Course guidance the project is measured against. |

The engineering journal is under [`journals/`](https://github.com/Pratham-90/ucs503p-aegis/tree/main/journals).

## The safety-critical rule

The catastrophic failure mode is **releasing a vault early**. Requirement
`NFR-REL-1` forbids any release before the check-in deadline *and* the full
grace period have elapsed with no confirmed check-in — verified by a dedicated
reliability suite. Everything in the design serves that guarantee.
