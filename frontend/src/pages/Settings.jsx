import { useEffect, useState } from "react";
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";
import { useApi } from "@/hooks/useApi";
import { api, errMsg } from "@/lib/api";
import { PageHeader, Section } from "@/components/DataTable";
import { AlertRulesForm } from "@/components/AlertRulesForm";

export default function Settings() {
  const { data } = useApi("/settings/report");
  const { data: alertData } = useApi("/settings/alerts");
  const [rules, setRules] = useState(null);
  useEffect(() => { if (alertData) setRules(alertData.rules); }, [alertData]);
  const saveRules = async () => {
    try { await api.put("/settings/alerts", rules); toast.success("Default alert rules saved"); } catch (e) { toast.error(errMsg(e)); }
  };
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (data) setNote(data.default_signoff || ""); }, [data]);
  const save = async () => {
    setBusy(true);
    try { await api.put("/settings/report", { default_signoff: note }); toast.success("Report settings saved"); } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <div>
      <PageHeader eyebrow="Administration" title="Report & alert settings" testid="settings-title" />
      <div className="px-10 py-8 max-w-3xl space-y-6">
        <Section title="Default technician sign-off note" testid="signoff-settings">
          <p className="text-sm text-[var(--tt-muted)] mb-3">
            This note is pre-filled on every report's cover page. Technicians can adjust it before exporting. The client name is taken from the computer's assigned client and site.
          </p>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={5} data-testid="default-signoff-input"
            placeholder="e.g. Inventory reviewed and verified on site. No unauthorized software found."
            className="w-full px-3 py-2.5 text-sm border border-[var(--tt-line)] rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--tt-blue)]/30" />
          <button onClick={save} disabled={busy} data-testid="save-settings-btn"
            className="mt-4 inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-[var(--tt-red)] text-white text-sm font-bold hover:bg-[#962810] transition-colors disabled:opacity-60">
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} Save
          </button>
        </Section>
        <Section title="Default alert rules" testid="alert-rules-settings">
          <p className="text-sm text-[var(--tt-muted)] mb-4">Choose which changes between scans raise an alert. Clients use these rules unless you set custom rules on the Clients & sites page.</p>
          {rules && <AlertRulesForm value={rules} onChange={setRules} prefix="default-rules" />}
          <button onClick={saveRules} data-testid="save-alert-rules-btn"
            className="mt-5 inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-[var(--tt-red)] text-white text-sm font-bold hover:bg-[#962810] transition-colors">
            <Save size={16} /> Save alert rules
          </button>
        </Section>
      </div>
    </div>
  );
}
