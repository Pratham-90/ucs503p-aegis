# Use-case diagram

Actors and the use cases they participate in. The **Scheduler** is modelled as a
*system actor*: it is time-triggered and initiates prompts and release with no
human action. Each use case is annotated with the functional requirement it
realises (see the [SRS](../srs/index.md#5-functional-requirements)).

```mermaid
flowchart LR
    owner[["👤 Owner"]]:::actor
    trustee[["👤 Trustee"]]:::actor
    scheduler{{"⏰ Scheduler<br/>(system actor)"}}:::sysactor

    subgraph AEGIS["Aegis system"]
        direction TB
        uc1(["Register / Log in<br/><b>FR-1</b>"])
        uc2(["Create vault &<br/>upload payload<br/><b>FR-2</b>"])
        uc3(["Configure interval<br/>& grace period<br/><b>FR-3</b>"])
        uc4(["Designate trustees,<br/>enrol keys, set K<br/><b>FR-4</b>"])
        uc5(["Issue check-in<br/>prompt<br/><b>FR-5</b>"])
        uc6(["Confirm check-in<br/>(one action)<br/><b>FR-6</b>"])
        uc7(["Distribute encrypted<br/>blobs on expiry<br/><b>FR-7</b>"])
        uc8(["Decrypt blob, combine<br/>K shares, decrypt<br/><b>FR-8</b>"])
    end

    owner --- uc1
    owner --- uc2
    owner --- uc3
    owner --- uc4
    owner --- uc6

    scheduler --- uc5
    scheduler --- uc7

    trustee --- uc8

    uc5 -. "prompts" .-> owner
    uc7 -. "delivers encrypted blob" .-> trustee

    classDef actor fill:#fff3cd,stroke:#b8860b,stroke-width:1px,color:#000;
    classDef sysactor fill:#e7f0ff,stroke:#3b6db5,stroke-width:1px,color:#000;
    classDef default fill:#ffffff,stroke:#888,color:#000;
```

## Notes

- **Owner** drives set-up (`FR-1`–`FR-4`) and keeps the vault closed by
  confirming check-ins (`FR-6`).
- **Scheduler** is the only actor that can move the vault toward release: it
  prompts (`FR-5`) and, *only* after the deadline and grace period lapse,
  distributes each trustee's **encrypted blob** (`FR-7`). This gate is the
  subject of `NFR-REL-1` (no early release).
- **Trustee** acts only after release, **decrypting their blob** and then
  combining `K` shares to reconstruct the key and decrypt the payload
  client-side (`FR-8`).

← Back to the [SRS](../srs/index.md) · see also the
[vault lifecycle](vault-lifecycle.md) and [architecture](architecture.md).
