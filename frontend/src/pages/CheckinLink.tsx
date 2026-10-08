import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api";
import { Alert, Card } from "../components/ui";

/** One-click check-in from the emailed link (FR-6, NFR-USE-1): opening the link *is* the action. */
export function CheckinLink() {
  const { token = "" } = useParams();
  const [result, setResult] = useState<{ kind: "success" | "warning" | "error"; text: string } | null>(null);
  const sent = useRef(false);

  useEffect(() => {
    if (sent.current) return; // StrictMode runs effects twice in development; POST once
    sent.current = true;
    api
      .post<{ deadline_at: string }>(`/checkin/${token}`)
      .then((r) =>
        setResult({ kind: "success", text: `You're checked in. Next check-in due ${new Date(r.deadline_at).toLocaleString()}.` }),
      )
      .catch((e) => {
        const messages: Record<string, string> = {
          token_used: "This link has already been used — you are checked in.",
          token_expired: "This link has expired. Log in to check in from your dashboard.",
          checkin_rejected: "Too late: the vault had already reached its release time.",
        };
        const code = e instanceof ApiError ? e.code : "";
        setResult({ kind: code === "token_used" ? "warning" : "error", text: messages[code] ?? (e as Error).message });
      });
  }, [token]);

  return (
    <div className="mx-auto max-w-lg">
      <Card title="Aegis check-in">
        {result ? <Alert kind={result.kind}>{result.text}</Alert> : <p className="text-sm text-slate-600 dark:text-slate-400">Confirming…</p>}
        <p className="mt-4 text-sm">
          <Link className="font-semibold text-indigo-700 dark:text-indigo-300" to="/dashboard">Open your dashboard</Link>
        </p>
      </Card>
    </div>
  );
}
