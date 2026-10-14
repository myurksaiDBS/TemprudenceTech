import { useEffect, useRef, useState } from "react";
import { BellRing, ImagePlus, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import { ClientLogo } from "@/components/ClientLogo";
import { AlertRulesForm } from "@/components/AlertRulesForm";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export const ClientLogoControl = ({ client, isAdmin, onDone }) => {
  const ref = useRef();
  const [busy, setBusy] = useState(false);
  const upload = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true);
    const fd = new FormData();
    fd.append("file", f);
    try { await api.post(`/clients/${client.id}/logo`, fd); toast.success("Logo uploaded"); onDone(); }
    catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); e.target.value = ""; }
  };
  const remove = async () => {
    try { await api.delete(`/clients/${client.id}/logo`); toast.success("Logo removed"); onDone(); } catch (err) { toast.error(errMsg(err)); }
  };
  return (
    <div className="flex items-center gap-3 mt-3">
      <div className="w-[120px] h-[56px] border border-[var(--tt-line)] rounded bg-white flex items-center justify-center overflow-hidden">
        {client.logo_path ? <ClientLogo clientId={client.id} version={client.logo_path} className="max-w-full max-h-full object-contain" testid={`client-logo-${client.name}`} />
          : <span className="text-[10px] text-[var(--tt-muted)] uppercase tracking-wide">No logo</span>}
      </div>
      {isAdmin && (
        <div className="flex flex-col gap-1">
          <input ref={ref} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={upload} data-testid={`client-logo-input-${client.name}`} />
          <button onClick={() => ref.current?.click()} disabled={busy} data-testid={`upload-logo-${client.name}`}
            className="inline-flex items-center gap-1 text-xs font-bold text-[var(--tt-blue)] hover:underline disabled:opacity-60">
            {busy ? <Loader2 size={12} className="animate-spin" /> : <ImagePlus size={12} />} {client.logo_path ? "Replace logo" : "Upload logo"}
          </button>
          {client.logo_path && (
            <button onClick={remove} data-testid={`remove-logo-${client.name}`} className="inline-flex items-center gap-1 text-xs font-bold text-[var(--tt-red)] hover:underline">
              <Trash2 size={12} /> Remove
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export const ClientRulesDialog = ({ client, onDone }) => {
  const { data: defaults } = useApi("/settings/alerts");
  const [open, setOpen] = useState(false);
  const [custom, setCustom] = useState(!!client.alert_rules);
  const [rules, setRules] = useState(client.alert_rules);
  useEffect(() => { if (!rules && defaults) setRules(defaults.rules); }, [defaults, rules]);
  const save = async () => {
    try {
      await api.put(`/clients/${client.id}/alert-rules`, { rules: custom ? rules : null });
      toast.success("Alert rules saved");
      setOpen(false);
      onDone();
    } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button data-testid={`alert-rules-${client.name}`} className="inline-flex items-center gap-1 text-[var(--tt-blue)] hover:underline">
          <BellRing size={14} /> Alert rules{client.alert_rules ? " (custom)" : ""}
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle className="text-[var(--tt-navy)]">Alert rules: {client.name}</DialogTitle></DialogHeader>
        <div className="flex rounded-md border border-[var(--tt-line)] p-1 mb-4">
          {[[false, "Use default rules"], [true, "Custom for this client"]].map(([v, l]) => (
            <button key={l} onClick={() => setCustom(v)} data-testid={`rules-mode-${v ? "custom" : "default"}`}
              className={`flex-1 px-3 py-1.5 text-sm font-semibold rounded transition-colors ${custom === v ? "bg-[var(--tt-blue)] text-white" : "text-[var(--tt-blue)]"}`}>{l}</button>
          ))}
        </div>
        {rules && <AlertRulesForm value={custom ? rules : defaults?.rules || rules} onChange={setRules} disabled={!custom} prefix="client-rules" />}
        <button onClick={save} data-testid="client-rules-save-btn" className="mt-5 w-full py-2.5 rounded-md bg-[var(--tt-blue)] text-white font-bold hover:bg-[var(--tt-navy)] transition-colors">Save</button>
      </DialogContent>
    </Dialog>
  );
};
