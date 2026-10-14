import { useState } from "react";
import { Link } from "react-router-dom";
import { AppWindow, CheckCheck, ShieldAlert, UserCog } from "lucide-react";
import { toast } from "sonner";
import { useApi } from "@/hooks/useApi";
import { api, errMsg, fmtDate } from "@/lib/api";
import { PageHeader } from "@/components/DataTable";
import { SeverityBadge } from "@/components/Status";

const KIND = { software: AppWindow, users: UserCog, security: ShieldAlert };

export default function Alerts() {
  const [status, setStatus] = useState("open");
  const { data, reload } = useApi("/alerts", { status });
  const alerts = data || [];
  const act = async (fn, msg) => { try { await fn(); toast.success(msg); reload(); } catch (e) { toast.error(errMsg(e)); } };
  return (
    <div>
      <PageHeader eyebrow="Change monitoring" title="Alerts" testid="alerts-title">
        <div className="flex rounded-md border border-[var(--tt-line)] bg-white p-1">
          {["open", "all"].map((s) => (
            <button key={s} onClick={() => setStatus(s)} data-testid={`alerts-filter-${s}`}
              className={`px-3 py-1.5 text-sm font-semibold rounded transition-colors ${status === s ? "bg-[var(--tt-blue)] text-white" : "text-[var(--tt-blue)]"}`}>
              {s === "open" ? "Open" : "All"}
            </button>
          ))}
        </div>
        {status === "open" && alerts.length > 0 && (
          <button onClick={() => act(() => api.post("/alerts/ack-all"), "All alerts acknowledged")} data-testid="ack-all-btn"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-[var(--tt-blue)] text-[var(--tt-blue)] text-sm font-bold hover:bg-[var(--tt-blue)] hover:text-white transition-colors">
            <CheckCheck size={16} /> Acknowledge all
          </button>
        )}
      </PageHeader>
      <div className="px-10 py-8 space-y-4">
        <p className="text-sm text-[var(--tt-muted)]">An alert is raised when a new scan shows apps installed or removed, account or administrator changes, or new security findings compared with the previous scan.</p>
        {alerts.length === 0 && <div className="tt-card p-8 text-center text-[var(--tt-muted)]" data-testid="alerts-empty">No {status === "open" ? "open " : ""}alerts.</div>}
        {alerts.map((a, i) => (
          <div key={a.id} className={`tt-card p-5 tt-rise ${a.acknowledged ? "opacity-70" : ""}`} style={{ animationDelay: `${i * 30}ms` }} data-testid={`alert-${i}`}>
            <div className="flex flex-wrap items-center gap-3 justify-between">
              <div className="flex items-center gap-3">
                <SeverityBadge severity={a.severity} />
                <Link to={`/computers/${a.computer_id}`} className="font-bold text-[var(--tt-blue)] hover:underline">{a.computer_name}</Link>
                <span className="text-xs text-[var(--tt-muted)]">{fmtDate(a.created_at)} · {a.run_type === "scheduled" ? "Weekly scheduled scan" : "Manual scan"}</span>
              </div>
              {a.acknowledged ? (
                <span className="text-xs text-[var(--tt-muted)]">Acknowledged by {a.acknowledged_by}</span>
              ) : (
                <button onClick={() => act(() => api.post(`/alerts/${a.id}/ack`), "Alert acknowledged")} data-testid={`ack-alert-${i}`}
                  className="text-sm font-bold text-[var(--tt-blue)] hover:underline">Acknowledge</button>
              )}
            </div>
            <ul className="mt-3 space-y-1.5">
              {a.items.map((it, j) => {
                const Icon = KIND[it.kind] || ShieldAlert;
                return <li key={j} className="flex items-start gap-2 text-sm text-[var(--tt-navy)]"><Icon size={15} className="mt-0.5 text-[var(--tt-muted)] shrink-0" />{it.text}</li>;
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
