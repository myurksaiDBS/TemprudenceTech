import { useState } from "react";
import { useApi } from "@/hooks/useApi";
import { PageHeader } from "@/components/DataTable";
import { ReportView } from "@/components/ReportView";
import { ExportButtons } from "@/components/ExportButtons";

export default function FleetReport() {
  const { data: comps } = useApi("/computers");
  const [sel, setSel] = useState([]);
  const ids = sel.join(",");
  const { data: report, loading } = useApi("/reports/fleet/data", { ids });
  const all = comps || [];
  const toggle = (id) => setSel((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  return (
    <div>
      <PageHeader eyebrow="Reports" title="Fleet summary" testid="fleet-report-title">
        <ExportButtons path="/reports/fleet/export" params={{ ids }} name="Temprudence_Fleet_Summary" showPrint />
      </PageHeader>
      <div className="px-6 lg:px-10 py-8 grid lg:grid-cols-[280px_1fr] gap-8">
        <aside className="no-print tt-card p-5 h-fit lg:sticky lg:top-6" data-testid="fleet-computer-picker">
          <div className="tt-eyebrow mb-3">Computers in report</div>
          <label className="flex items-center gap-2 text-sm font-semibold mb-3 cursor-pointer">
            <input type="checkbox" checked={sel.length === 0} onChange={() => setSel([])} className="accent-[var(--tt-blue)] w-4 h-4" data-testid="fleet-select-all" />
            All computers ({all.length})
          </label>
          <div className="space-y-2 max-h-[420px] overflow-auto border-t border-[var(--tt-line)] pt-3">
            {all.map((c) => (
              <label key={c.id} className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={sel.includes(c.id)} onChange={() => toggle(c.id)} className="accent-[var(--tt-blue)] w-4 h-4" data-testid={`fleet-select-${c.name}`} />
                <span className="truncate">{c.name}</span>
              </label>
            ))}
          </div>
          <p className="text-xs text-[var(--tt-muted)] mt-4">Pick specific computers, or leave “All computers” checked.</p>
        </aside>
        <div className={loading ? "opacity-60 transition-opacity" : "transition-opacity"}>{report && <ReportView report={report} />}</div>
      </div>
    </div>
  );
}
