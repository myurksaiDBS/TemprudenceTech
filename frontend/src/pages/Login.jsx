import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { Loader2, LockKeyhole } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { errMsg } from "@/lib/api";

export default function Login() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      nav("/");
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-[1.1fr_1fr]">
      <div className="bg-white flex flex-col items-center justify-center px-10 py-16 border-r border-[var(--tt-line)]">
        <img src="/brand/logo.png" alt="Temprudence Technologies" className="w-[340px] max-w-full tt-rise" data-testid="login-logo" />
        <p className="mt-6 text-sm text-[var(--tt-muted)] text-center max-w-sm tt-rise" style={{ animationDelay: "120ms" }}>
          Windows computer inventory for operating systems, software, hardware, networks and user privileges.
        </p>
      </div>
      <div className="bg-[var(--tt-navy)] flex items-center justify-center px-8 py-16">
        <form onSubmit={submit} className="w-full max-w-sm tt-rise" style={{ animationDelay: "200ms" }} data-testid="login-form">
          <div className="flex items-center gap-2 text-white/70 tt-eyebrow !text-white/70">
            <LockKeyhole size={14} /> Secure sign-in
          </div>
          <h1 className="text-4xl font-bold text-white mt-3">Inventory Console</h1>
          <p className="text-white/70 text-sm mt-2 mb-10">Sign in with the account your administrator created.</p>
          <label className="block text-xs font-semibold text-white/80 mb-1.5" htmlFor="email">Email</label>
          <input
            id="email" type="email" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)}
            data-testid="login-email-input"
            className="w-full rounded-md px-3.5 py-2.5 bg-white/95 text-[var(--tt-navy)] focus:outline-none focus:ring-2 focus:ring-white/60 mb-5"
          />
          <label className="block text-xs font-semibold text-white/80 mb-1.5" htmlFor="password">Password</label>
          <input
            id="password" type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)}
            data-testid="login-password-input"
            className="w-full rounded-md px-3.5 py-2.5 bg-white/95 text-[var(--tt-navy)] focus:outline-none focus:ring-2 focus:ring-white/60"
          />
          {error && <div className="mt-4 text-sm bg-[#fbeae5] text-[var(--tt-red)] rounded-md px-3 py-2 font-semibold" data-testid="login-error">{error}</div>}
          <button
            type="submit" disabled={busy} data-testid="login-submit-btn"
            className="mt-8 w-full inline-flex items-center justify-center gap-2 rounded-md py-3 font-bold text-white bg-[var(--tt-red)] hover:bg-[#962810] transition-colors disabled:opacity-70"
          >
            {busy && <Loader2 size={16} className="animate-spin" />} Sign in
          </button>
          <p className="text-[11px] text-white/50 mt-10">Temprudence Technologies · A Division of YFI Enterprises, LLC</p>
        </form>
      </div>
    </div>
  );
}
