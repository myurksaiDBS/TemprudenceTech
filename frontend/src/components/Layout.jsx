import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { LayoutDashboard, Monitor, ScanLine, FileText, Users, LogOut, Building2, Bell, Settings } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, id: "dashboard", end: true },
  { to: "/alerts", label: "Alerts", icon: Bell, id: "alerts" },
  { to: "/computers", label: "Computers", icon: Monitor, id: "computers" },
  { to: "/clients", label: "Clients & sites", icon: Building2, id: "clients" },
  { to: "/scan", label: "Scan a computer", icon: ScanLine, id: "scan" },
  { to: "/reports", label: "Fleet report", icon: FileText, id: "reports" },
  { to: "/users", label: "Users", icon: Users, id: "users", admin: true },
  { to: "/settings", label: "Report settings", icon: Settings, id: "settings", admin: true },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const { data: alerts } = useApi("/alerts", { status: "open", _: loc.pathname });
  const openAlerts = alerts?.length || 0;
  return (
    <div className="min-h-screen flex">
      <aside className="no-print w-[264px] shrink-0 bg-white border-r border-[var(--tt-line)] flex flex-col sticky top-0 h-screen" data-testid="sidebar">
        <div className="px-[22px] pt-5 pb-4 border-b border-[var(--tt-line)]">
          <img src="/brand/logo.png" alt="Temprudence Technologies" className="w-[220px] h-auto block" data-testid="header-logo" />
        </div>
        <div className="px-4 pt-4 pb-2 tt-eyebrow">Inventory console</div>
        <nav className="flex-1 px-3 space-y-1">
          {NAV.filter((n) => !n.admin || user?.role === "admin").map(({ to, label, icon: Icon, id, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              data-testid={`nav-${id}`}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-semibold transition-colors duration-150 ${
                  isActive ? "bg-[var(--tt-blue)] text-white" : "text-[var(--tt-blue)] hover:bg-[#eef3f8]"
                }`
              }
            >
              <Icon size={18} strokeWidth={2} />
              <span className="flex-1">{label}</span>
              {id === "alerts" && openAlerts > 0 && (
                <span data-testid="nav-alerts-badge" className="min-w-[22px] text-center text-[11px] font-bold px-1.5 py-0.5 rounded-full bg-[var(--tt-red)] text-white">{openAlerts}</span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-[var(--tt-line)] bg-[var(--tt-navy)] text-white">
          <div className="text-sm font-semibold truncate" data-testid="current-user-name">{user?.name}</div>
          <div className="text-xs text-white/70 truncate">{user?.email}</div>
          <div className="flex items-center justify-between mt-3">
            <span className="text-[10px] uppercase tracking-[0.14em] font-bold px-2 py-0.5 rounded bg-white/10" data-testid="current-user-role">{user?.role}</span>
            <button
              data-testid="logout-btn"
              onClick={async () => { await logout(); nav("/login"); }}
              className="flex items-center gap-1.5 text-xs font-semibold text-white/80 hover:text-white transition-colors"
            >
              <LogOut size={14} /> Sign out
            </button>
          </div>
        </div>
      </aside>
      <main className="flex-1 min-w-0">
        <Outlet />
        <footer className="no-print px-10 py-6 text-xs text-[var(--tt-muted)] border-t border-[var(--tt-line)]">
          Temprudence Technologies · A Division of YFI Enterprises, LLC · Veteran Owned · Faith Based · Ethical · Principled
        </footer>
      </main>
    </div>
  );
}
