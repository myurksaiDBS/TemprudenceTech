import { useState } from "react";
import { Building2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useApi } from "@/hooks/useApi";
import { api, errMsg } from "@/lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export const ClientAssign = ({ computer, onDone }) => {
  const { data } = useApi("/clients");
  const [open, setOpen] = useState(false);
  const [clientId, setClientId] = useState(computer.client_id || "");
  const [site, setSite] = useState(computer.site || "");
  const [busy, setBusy] = useState(false);
  const clients = data?.clients || [];
  const current = clients.find((c) => c.id === computer.client_id);
  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.patch(`/computers/${computer.id}`, { client_id: clientId, site });
      toast.success("Client assignment saved");
      setOpen(false);
      onDone();
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <span className="flex items-center gap-1">
        <span className="text-[var(--tt-muted)]">Client </span>
        <span data-testid="computer-client">{current ? `${current.name}${computer.site ? ` · ${computer.site}` : ""}` : "Unassigned"}</span>
        <DialogTrigger asChild>
          <button data-testid="assign-client-btn" className="text-[var(--tt-blue)] hover:text-[var(--tt-red)] transition-colors" aria-label="Assign client"><Building2 size={14} /></button>
        </DialogTrigger>
      </span>
      <DialogContent>
        <DialogHeader><DialogTitle className="text-[var(--tt-navy)]">Assign {computer.name} to a client</DialogTitle></DialogHeader>
        <form onSubmit={save}>
          <label className="block mb-4">
            <span className="block text-xs font-semibold text-[var(--tt-muted)] mb-1">Client</span>
            <select value={clientId} onChange={(e) => setClientId(e.target.value)} data-testid="assign-client-select"
              className="w-full px-3 py-2 text-sm border border-[var(--tt-line)] rounded-md bg-white">
              <option value="">Unassigned</option>
              {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          <label className="block mb-2">
            <span className="block text-xs font-semibold text-[var(--tt-muted)] mb-1">Site (optional)</span>
            <input value={site} onChange={(e) => setSite(e.target.value)} placeholder="e.g. Main office" data-testid="assign-site-input"
              className="w-full px-3 py-2 text-sm border border-[var(--tt-line)] rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--tt-blue)]/30" />
          </label>
          <p className="text-xs text-[var(--tt-muted)] mb-5">Manual assignment overrides the client set by the upload key on future scans.</p>
          <button type="submit" disabled={busy} data-testid="assign-client-save-btn"
            className="w-full inline-flex justify-center items-center gap-2 py-2.5 rounded-md bg-[var(--tt-blue)] text-white font-bold hover:bg-[var(--tt-navy)] transition-colors disabled:opacity-60">
            {busy && <Loader2 size={16} className="animate-spin" />} Save
          </button>
        </form>
      </DialogContent>
    </Dialog>
  );
};
