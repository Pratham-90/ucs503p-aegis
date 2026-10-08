import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { Logo } from "../components/Layout";

const STEPS = [
  { n: 1, title: "Encrypt", body: "Your browser encrypts the message or file with AES-256-GCM. The key never leaves your device." },
  { n: 2, title: "Split", body: "The key is split with Shamir's Secret Sharing: any K of your N trustees can rebuild it, K−1 learn nothing." },
  { n: 3, title: "Check in", body: "Aegis asks you to check in on a schedule. One click resets the clock and the vault stays sealed." },
  { n: 4, title: "Release", body: "If you stop responding and the grace period ends, trustees receive their encrypted shares and K of them open the vault." },
];

export function Landing() {
  const { owner } = useAuth();
  return (
    <div className="space-y-10">
      <section className="grid items-center gap-8 rounded-3xl bg-slate-900 px-6 py-10 text-white sm:px-10 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <p className="text-sm font-semibold uppercase tracking-widest text-indigo-300">Encrypted legacy vault</p>
          <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-5xl">
            Your secrets reach the right people, only when you no longer can.
          </h1>
          <p className="mt-4 max-w-2xl text-base text-slate-300 sm:text-lg">
            Aegis is a dead-man's switch: miss your check-ins and, after a grace period, your trustees can open what you
            left them. No one opens it early, and no single person can open it alone.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to={owner ? "/dashboard" : "/register"} className="rounded-lg bg-indigo-500 px-5 py-2.5 text-sm font-semibold hover:bg-indigo-400">
              {owner ? "Go to your dashboard" : "Create your vault"}
            </Link>
            <Link to="/demo" className="rounded-lg px-5 py-2.5 text-sm font-semibold ring-1 ring-slate-600 hover:bg-slate-800">
              Open the demo console
            </Link>
          </div>
        </div>
        <div className="flex justify-center">
          <Logo className="h-40 w-40 drop-shadow-xl sm:h-56 sm:w-56" />
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-slate-900">How it works</h2>
        <ol className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s) => (
            <li key={s.n} className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-sm font-bold text-white">{s.n}</span>
              <h3 className="mt-3 font-semibold text-slate-900">{s.title}</h3>
              <p className="mt-1 text-sm text-slate-600">{s.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <h2 className="font-semibold text-slate-900">Trust model, in one line</h2>
        <p className="mt-1 text-sm text-slate-700">
          The server is trusted to keep time and deliver messages, never to read your vault: it stores only ciphertext
          and shares encrypted to each trustee's own key.
        </p>
      </section>
    </div>
  );
}
