import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api";
import { useAuth } from "../auth";
import { Alert, Button, Card, Field, inputClass } from "../components/ui";

function AuthForm({ mode }: { mode: "register" | "login" }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { refresh } = useAuth();
  const navigate = useNavigate();

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.post(`/auth/${mode}`, { email, password });
      await refresh();
      navigate("/dashboard");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const isRegister = mode === "register";
  return (
    <div className="mx-auto max-w-md">
      <Card title={isRegister ? "Create your account" : "Log in"} subtitle={isRegister ? "You are the Owner of the vault." : undefined}>
        <form className="space-y-4" onSubmit={submit}>
          <Field label="Email">
            <input className={inputClass} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label="Password" hint={isRegister ? "At least 8 characters. Stored only as an Argon2id hash." : undefined}>
            <input
              className={inputClass}
              type="password"
              autoComplete={isRegister ? "new-password" : "current-password"}
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
          {error && <Alert kind="error">{error}</Alert>}
          <Button type="submit" busy={busy} className="w-full">
            {isRegister ? "Create account" : "Log in"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-slate-600 dark:text-slate-400">
          {isRegister ? (
            <>Already registered? <Link className="font-semibold text-indigo-700 dark:text-indigo-300" to="/login">Log in</Link></>
          ) : (
            <>New here? <Link className="font-semibold text-indigo-700 dark:text-indigo-300" to="/register">Create an account</Link></>
          )}
        </p>
      </Card>
    </div>
  );
}

export const Register = () => <AuthForm mode="register" />;
export const Login = () => <AuthForm mode="login" />;
