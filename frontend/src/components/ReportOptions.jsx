import { useEffect, useState } from "react";
import { PenLine } from "lucide-react";
import { useApi } from "@/hooks/useApi";

export const ReportOptions = ({ defaultClient, onApply }) => {
  const { data: settings } = useApi("/settings/report");
  const [client, setClient] = useState("");
  const [signoff, setSignoff] = useState("");
  useEffect(() => { setClient(defaultClient || ""); }, [defaultClient]);
  useEffect(() => { if (settings) setSignoff(settings.default_signoff || ""); }, [settings]);
  const apply = () => onApply({ client_name: client, signoff });
  return (
    <div className="no-print tt-card p-5 max-w-[980px] mx-auto mb-6" data-testid="report-options">
      <div className="flex items-center gap-2 tt-eyebrow mb-3"><PenLine size={14} /> Cover page</div>
      <div className="grid md:grid-cols-[1fr_2fr] gap-4">
        <label className="block">
          <span className="block text-xs font-semibold text-[var(--tt-muted)] mb-1">Prepared for (client)</span>
          <input value={client} onChange={(e) => setClient(e.target.value)} onBlur={apply} data-testid="report-client-input" placeholder="Client name"
            className="w-full px-3 py-2 text-sm border border-[var(--tt-line)] rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--tt-blue)]/30" />
        </label>
        <label className="block">
          <span className="block text-xs font-semibold text-[var(--tt-muted)] mb-1">Technician sign-off note</span>
          <textarea value={signoff} onChange={(e) => setSignoff(e.target.value)} onBlur={apply} rows={2} data-testid="report-signoff-input" placeholder="Optional note shown on the cover page"
            className="w-full px-3 py-2 text-sm border border-[var(--tt-line)] rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--tt-blue)]/30" />
        </label>
      </div>
      <p className="text-xs text-[var(--tt-muted)] mt-2">Changes apply to the preview below and to Word, ODT and PDF exports.</p>
    </div>
  );
};
