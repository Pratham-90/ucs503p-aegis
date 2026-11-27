import { useEffect, useState } from "react";
import { formatDuration } from "./ui";

/**
 * Counts down to ``target`` using the *server's* clock: ``offsetMs`` is
 * (server_now - Date.now()) captured when the data was fetched, so the demo
 * fast-forward and any client clock skew are both accounted for.
 */
export function Countdown({ target, offsetMs, label }: { target: string | null; offsetMs: number; label: string }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  if (!target) return null;
  const remaining = (new Date(target).getTime() - (now + offsetMs)) / 1000;
  return (
    <div className="glass-inset rounded-xl p-4">
      <div className="font-mono text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500 dark:text-slate-400">{label}</div>
      <div className="mt-2 font-mono text-2xl font-semibold tabular-nums tracking-tight text-slate-900 dark:text-white" data-testid={`countdown-${label}`}>
        {remaining > 0 ? formatDuration(remaining) : "due now"}
      </div>
      <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{new Date(target).toLocaleString()}</div>
    </div>
  );
}
