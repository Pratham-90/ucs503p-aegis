/** Thin fetch wrapper for the same-origin FastAPI backend (all routes under /api). */

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(method: string, path: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    credentials: "same-origin",
    headers: { ...(body !== undefined ? { "Content-Type": "application/json" } : {}), ...headers },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const err = data?.error ?? {};
    throw new ApiError(response.status, err.code ?? `http_${response.status}`, err.message ?? response.statusText, err);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, headers?: Record<string, string>) => request<T>("GET", path, undefined, headers),
  post: <T>(path: string, body?: unknown, headers?: Record<string, string>) => request<T>("POST", path, body ?? {}, headers),
};

export type VaultState = "setup" | "active" | "warning" | "grace" | "released";

export interface Owner {
  id: string;
  email: string;
}

export interface TrusteeSummary {
  id: string;
  position: number;
  email: string;
  enrolled: boolean;
  enrolled_at: string | null;
  public_key_jwk: JsonWebKey | null;
}

export interface VaultSummary {
  id: string;
  state: VaultState;
  k: number;
  n: number;
  loss_tolerance: number;
  warnings: string[];
  interval_s: number;
  grace_s: number;
  warning_s: number;
  deadline_at: string | null;
  grace_starts_at: string | null;
  release_at: string | null;
  last_checkin_at: string | null;
  armed_at: string | null;
  released_at: string | null;
  payload_uploaded: boolean;
  all_enrolled: boolean;
  trustees: TrusteeSummary[];
  checkins: { at: string; source: string }[];
  server_now: string;
}

export interface Invite {
  trustee_id: string;
  position: number;
  email: string;
  link: string;
}

export interface ServerView {
  table: string;
  row: Record<string, unknown>;
  share_blobs: Record<string, unknown>[];
  trustee_public_keys: Record<string, unknown>[];
  never_received: string[];
}

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}
