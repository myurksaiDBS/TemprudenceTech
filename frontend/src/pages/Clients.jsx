import { useState } from "react";
import { Link } from "react-router-dom";
import { Building2, FileText, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useApi } from "@/hooks/useApi";
import { useAuth } from "@/context/AuthContext";
import { api, errMsg } from "@/lib/api";
import { PageHeader } from "@/components/DataTable";

export default function Clients() {
  const { user } = useAuth();
  const { data, reload } = useApi("/clients");
  const [name, setName] = useState("");
  const clients = data?.clients || [];
  const act = async (fn, msg) => { try { await fn(); toast.success(msg); reload(); } catch (e) { toast.error(errMsg(e)); } };
  const create = (e) => { e.preventDefault(); act(() => api.post("/clients", { name }), "Client created").then(() => setName("")); };
  const rename = (c) => { const n = window.prompt("Client name", c.name); if (n && n.trim()) act(() => api.patch(`/clients/${c.id}`, { name: n, notes: c.notes }), "Client renamed"); };
  const remove = (c) => window.confirm(`Delete client "${c.name}"? Its ${c.computer_count} computer(s) become unassigned.`) && act(() => api.delete(`/clients/${c.id}`), "Client deleted");

  return (
    <div>
      <PageHeader eyebrow="Organize" title="Clients & sites" testid="clients-title" />
      <div className="px-10 py-8 space-y-6">
        <form onSubmit={create} className="tt-card p-5 flex flex-wrap gap-3 items-center tt-rise" data-testid="new-client-form">
          <Building2 size={18} className="text-[var(--tt-blue)]" />
          <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="New client name, e.g. Acme Dental" data-testid="new-client-name-input"
            className="flex-1 min-w-[240px] px-3 py-2.5 text-sm border border-[var(--tt-line)] rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--tt-blue)]/30" />
          <button type="submit" data-testid="create-client-btn" className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-[var(--tt-red)] text-white text-sm font-bold hover:bg-[#962810] transition-colors">
            <Plus size={16} /> Add client
          </button>
        </form>
        <p className="text-sm text-[var(--tt-muted)]">
          Assign computers on each computer page, or create an upload key for a client and site on the Scan page so new scans are grouped automatically.
        </p>
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {clients.map((c, i) => (
            <div key={c.id} className="tt-card p-5 tt-rise" style={{ animationDelay: `${i * 40}ms` }} data-testid={`client-card-${c.name}`}>
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-lg font-bold text-[var(--tt-navy)]">{c.name}</h3>
                <div className="flex gap-2">
                  <button onClick={() => rename(c)} data-testid={`rename-client-${c.name}`} className="text-[var(--tt-muted)] hover:text-[var(--tt-blue)]" aria-label="Rename"><Pencil size={15} /></button>
                  {user?.role === "admin" && (
                    <button onClick={() => remove(c)} data-testid={`delete-client-${c.name}`} className="text-[var(--tt-muted)] hover:text-[var(--tt-red)]" aria-label="Delete"><Trash2 size={15} /></button>
                  )}
                </div>
              </div>
              <div className="flex gap-6 mt-3 text-sm">
                <div><div className="text-2xl font-bold text-[var(--tt-blue)]">{c.computer_count}</div><div className="tt-eyebrow">Computers</div></div>
                <div><div className={`text-2xl font-bold ${c.critical_count ? "text-[var(--tt-red)]" : "text-[var(--tt-navy)]"}`}>{c.critical_count}</div><div className="tt-eyebrow">Critical</div></div>
              </div>
              <div className="text-xs text-[var(--tt-muted)] mt-3">Sites: {c.sites.length ? c.sites.join(", ") : "None"}</div>
              <div className="flex gap-4 mt-4 pt-3 border-t border-[var(--tt-line)] text-sm font-semibold">
                <Link to={`/computers?client=${c.id}`} className="text-[var(--tt-blue)] hover:underline" data-testid={`client-computers-${c.name}`}>View computers</Link>
                <Link to={`/reports?client=${c.id}`} className="text-[var(--tt-red)] hover:underline inline-flex items-center gap-1" data-testid={`client-report-${c.name}`}><FileText size={14} /> Client report</Link>
              </div>
            </div>
          ))}
          <div className="tt-card p-5 border-dashed" data-testid="client-card-unassigned">
            <h3 className="text-lg font-bold text-[var(--tt-muted)]">Unassigned</h3>
            <div className="text-2xl font-bold text-[var(--tt-navy)] mt-3">{data?.unassigned ?? 0}</div>
            <div className="tt-eyebrow">Computers</div>
            <Link to="/computers?client=none" className="inline-block mt-4 text-sm font-semibold text-[var(--tt-blue)] hover:underline">View computers</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
