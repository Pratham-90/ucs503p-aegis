import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { Layout } from "./components/Layout";
import "./index.css";
import { Login, Register } from "./pages/Auth";
import { CheckinLink } from "./pages/CheckinLink";
import { Dashboard } from "./pages/Dashboard";
import { DemoConsole } from "./pages/DemoConsole";
import { Landing } from "./pages/Landing";
import { Recover } from "./pages/Recover";
import { TrusteeEnrol } from "./pages/TrusteeEnrol";
import { TrusteePortal } from "./pages/TrusteePortal";
import { VaultNew } from "./pages/VaultNew";

function RequireOwner({ children }: { children: React.ReactElement }) {
  const { owner, loading } = useAuth();
  if (loading) return <p className="text-sm text-slate-500">Loading…</p>;
  return owner ? children : <Navigate to="/login" replace />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Landing />} />
            <Route path="/register" element={<Register />} />
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={<RequireOwner><Dashboard /></RequireOwner>} />
            <Route path="/vault/new" element={<RequireOwner><VaultNew /></RequireOwner>} />
            <Route path="/checkin/:token" element={<CheckinLink />} />
            <Route path="/trustee/enrol/:token" element={<TrusteeEnrol />} />
            <Route path="/trustee" element={<TrusteePortal />} />
            <Route path="/recover" element={<Recover />} />
            <Route path="/demo" element={<DemoConsole />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
