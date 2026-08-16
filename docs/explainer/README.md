# Aegis — animated explainer

A single, self-contained HTML file (`index.html`) that plays a ~60-second
animated overview of Aegis. No build step, no npm, no external dependencies —
just inline CSS and vanilla JavaScript driving an animated SVG. Made to be
projected and screen-recorded.

## Run it

Open the file in any modern browser:

- **Double-click** `index.html`, or
- drag it into a browser window, or
- serve the folder and visit it:

```bash
python -m http.server 8000
# then open http://localhost:8000/docs/explainer/  (run from the repo root)
```

It **autoplays on load** and runs for about 60 seconds. Click **↻ Replay**
(bottom-right) to restart.

## What it shows (5 scenes, ~60 s)

| # | ~Time | Scene |
| - | ----- | ----- |
| 1 | 0–8 s | **The problem** — you hold secrets; two bad options: expose them now, or lose them forever. |
| 2 | 8–20 s | **The check-in loop** — a timer cycles, the owner confirms, the vault stays sealed (shown repeating). |
| 3 | 20–32 s | **Silence** — the owner stops responding; the state machine runs Active → Warning → Grace → Released as the countdown empties. |
| 4 | 32–50 s | **Splitting the key** (centrepiece) — the key splits into 5 shares to 5 trustees, then: 2 shares admit many curves (key undetermined), 3 shares pin exactly one curve (the key). |
| 5 | 50–60 s | **The guarantee** — the vault opens; one line on what Aegis promises. |

Scene 4 is **conceptually honest**: for a threshold of `K = 3` the key lives on a
degree-2 polynomial (a parabola). The animation shows that **2 points admit a
whole family of parabolas** hitting the `f(0)` axis at different heights (the
key could be anything), while **3 points determine exactly one** parabola and
therefore one value of `f(0)` — the key. This mirrors Shamir's Secret Sharing as
implemented in `code/spikes/shamir_spike.py`: any `K` shares reconstruct the
secret, any `K−1` reveal nothing.

## How to screen-record it

**Windows (built-in):**

1. Open `index.html` in a browser; press **F11** for fullscreen so only the
   animation is visible.
2. Press **Win + Alt + R** (Xbox Game Bar) to start/stop recording, or open
   Game Bar with **Win + G** first. The clip lands in
   `Videos\Captures` as an MP4.
3. Click **↻ Replay** to re-run for a clean take.

**Cross-platform options:** OBS Studio (Display or Window Capture), or Chrome
DevTools' built-in recorder. Record at 1080p; the layout is a 16:9 SVG
(`viewBox 1280×720`) and scales cleanly.

**Tips**

- Let the page finish loading before you hit record, then click **↻ Replay** so
  the run starts from frame 0.
- The animation is driven by `requestAnimationFrame`; keep the tab focused and
  visible while recording (background tabs throttle animation).
- Total runtime is ~60 s; leave a second of padding at each end.

## Notes

- Everything is inline in `index.html` — safe to copy the file anywhere and it
  still works offline.
- This is a presentation aid, not part of the application. It is not wired into
  the mkdocs navigation.
