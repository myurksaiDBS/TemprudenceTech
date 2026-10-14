import { useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, fmtDate } from "@/lib/api";
import { Section } from "@/components/DataTable";

export const KeysPanel = ({ keys, reload, isAdmin }) => {
  const [label, setLabel] = useState("");
  const create = async (e) => {
    e.preventDefault();
    try { await api.post("/keys", { label }); setLabel(""); toast.success("Upload key created"); reload(); } catch (err) { toast.error(errMsg(err)); }
  };
  const revoke = async (k) => {
    if (!window.confirm(`Revoke "${k.label}"? Scanners using it will stop uploading.`)) return;
    try { await api.post(`/keys/${k.id}/revoke`); toast.success("Key revoked"); reload(); } catch (err) { toast.error(errMsg(err)); }
  };
  return (
    <Section title="Upload keys" testid="keys-panel">
      <ul className="divide-y divide-[var(--tt-line)] mb-4">
        {keys.map((k) => (
          <li key={k.id} className="py-2.5 flex items-center justify-between gap-3" data-testid={`key-row-${k.label}`}>
            <div className="min-w-0">
              <div className="text-sm font-semibold">{k.label} {!k.active && <span className="text-[10px] uppercase font-bold text-[var(--tt-red)] ml-1">Revoked</span>}</div>
              <div className="text-[11px] text-[var(--tt-muted)]">Uploads: {k.use_count} · Created {fmtDate(k.created_at)}</div>
            </div>
            {isAdmin && k.active && (
              <button onClick={() => revoke(k)} data-testid={`revoke-key-${k.label}`} className="text-xs font-bold text-[var(--tt-red)] hover:underline">Revoke</button>
            )}
          </li>
        ))}
      </ul>
      {isAdmin ? (
        <form onSubmit={create} className="flex gap-2">
          <input value={label} onChange={(e) => setLabel(e.target.value)} required placeholder="Label, e.g. Client: Acme Dental" data-testid="new-key-label-input"
            className="flex-1 px-3 py-2 text-sm border border-[var(--tt-line)] rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--tt-blue)]/30" />
          <button type="submit" data-testid="create-key-btn" className="inline-flex items-center gap-1 px-3 py-2 rounded-md bg-[var(--tt-blue)] text-white text-sm font-bold hover:bg-[var(--tt-navy)] transition-colors">
            <Plus size={15} /> Create
          </button>
        </form>
      ) : <p className="text-xs text-[var(--tt-muted)]">Only administrators can create or revoke keys.</p>}
    </Section>
  );
};
