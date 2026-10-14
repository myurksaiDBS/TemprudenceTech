import { Link, Outlet, useNavigate } from "react-router-dom";
import { LogOut } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { ClientLogo } from "@/components/ClientLogo";

export default function PortalLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const { data } = useApi("/portal/overview");
  const client = data?.client;
  return (
    <div className="min-h-screen flex flex-col">
      <header className="no-print bg-white border-b border-[var(--tt-line)]" data-testid="portal-header">
        <div className="max-w-[1280px] mx-auto px-8 py-4 flex flex-wrap items-center gap-8 justify-between">
          <Link to="/portal" className="flex items-center gap-8" data-testid="portal-home-link">
            <img src="/brand/logo.png" alt="Temprudence Technologies" className="w-[220px] h-auto" />
            {client?.has_logo && (
              <ClientLogo clientId={client.id} className="max-h-[110px] max-w-[200px] object-contain" testid="portal-client-logo" />
            )}
          </Link>
          <div className="text-right">
            <div className="tt-eyebrow">Client portal</div>
            <div className="text-xl font-bold text-[var(--tt-navy)]" data-testid="portal-client-name">{client?.name}</div>
            <div className="flex items-center justify-end gap-4 mt-1 text-sm">
              <span className="text-[var(--tt-muted)]" data-testid="portal-user-name">{user?.name}</span>
              <button data-testid="logout-btn" onClick={async () => { await logout(); nav("/login"); }}
                className="inline-flex items-center gap-1.5 font-semibold text-[var(--tt-blue)] hover:text-[var(--tt-red)] transition-colors">
                <LogOut size={14} /> Sign out
              </button>
            </div>
          </div>
        </div>
      </header>
      <main className="flex-1">
        <Outlet context={data} />
      </main>
      <footer className="no-print px-8 py-6 text-xs text-[var(--tt-muted)] border-t border-[var(--tt-line)] text-center">
        Prepared by Temprudence Technologies · A Division of YFI Enterprises, LLC · Read-only client access
      </footer>
    </div>
  );
}
