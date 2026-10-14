import { useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, fmtDate } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import { Section } from "@/components/DataTable";

export const KeysPanel = ({ keys, reload, isAdmin }) => {
  const [label, setLabel] = useState("");
  const [clientId, setClientId] = useState("");
  const [site, setSite] = useState("");
  const { data } = useApi("/clients");
  const clients = data?.clients || [];
  const create = async (e) => {
    e.preventDefault();
    try {
      await api.post("/keys", { label, client_id: clientId || null, site });
      setLabel(""); setSite(""); setClientId("");
      toast.success("Upload key created");
      reload();
    } catch (err) { toast.error(errMsg(err)); }
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
              <div className="text-[11px] text-[var(--tt-muted)]">
                {k.client_id ? `Auto-assigns to ${clients.find((c) => c.id === k.client_id)?.name || "client"}${k.site ? ` · ${k.site}` : ""} · ` : ""}Uploads: {k.use_count} · Created {fmtDate(k.created_at)}
              </div>
            </div>
            {isAdmin && k.active && (
              <button onClick={() => revoke(k)} data-testid={`revoke-key-${k.label}`} className="text-xs font-bold text-[var(--tt-red)] hover:underline">Revoke</button>
            )}
          </li>
        ))}
      </ul>
      {isAdmin ? (
        <form onSubmit={create} className="grid grid-cols-2 gap-2">
          <input value={label} onChange={(e) => setLabel(e.target.value)} required placeholder="Label, e.g. Acme Dental - Main office" data-testid="new-key-label-input"
            className="col-span-2 px-3 py-2 text-sm border border-[var(--tt-line)] rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--tt-blue)]/30" />
          <select value={clientId} onChange={(e) => setClientId(e.target.value)} data-testid="new-key-client-select"
            className="px-3 py-2 text-sm border border-[var(--tt-line)] rounded-md bg-white">
            <option value="">No client (unassigned)</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <input value={site} onChange={(e) => setSite(e.target.value)} placeholder="Site (optional)" data-testid="new-key-site-input"
            className="px-3 py-2 text-sm border border-[var(--tt-line)] rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--tt-blue)]/30" />
          <button type="submit" data-testid="create-key-btn" className="col-span-2 justify-center inline-flex items-center gap-1 px-3 py-2 rounded-md bg-[var(--tt-blue)] text-white text-sm font-bold hover:bg-[var(--tt-navy)] transition-colors">
            <Plus size={15} /> Create
          </button>
        </form>
      ) : <p className="text-xs text-[var(--tt-muted)]">Only administrators can create or revoke keys.</p>}
    </Section>
  );
};
