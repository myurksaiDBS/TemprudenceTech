import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { PageHeader } from "@/components/DataTable";
import { ReportView } from "@/components/ReportView";
import { ExportButtons } from "@/components/ExportButtons";
import { ReportOptions } from "@/components/ReportOptions";

export default function ComputerReport() {
  const { id } = useParams();
  const [sp] = useSearchParams();
  const scanId = sp.get("scan_id");
  const [opts, setOpts] = useState({});
  const params = { ...(scanId ? { scan_id: scanId } : {}), ...opts };
  const { data, error } = useApi(`/reports/computer/${id}/data`, params);
  const [autoClient, setAutoClient] = useState(null);
  if (data && autoClient === null) {
    const row = data.meta.find((m) => m[0] === "Prepared for");
    setAutoClient(row ? row[1] : "");
  }
  return (
    <div>
      <PageHeader eyebrow="Computer inventory report" title={data?.subtitle || "Report"} testid="computer-report-title">
        <Link to={`/computers/${id}`} className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-semibold text-[var(--tt-muted)] hover:text-[var(--tt-navy)]" data-testid="back-to-computer-btn">
          <ArrowLeft size={15} /> Back
        </Link>
        <ExportButtons path={`/reports/computer/${id}/export`} params={params} name={`Temprudence_Inventory_${data?.subtitle || id}`} showPrint />
      </PageHeader>
      <div className="px-6 py-8">
        {autoClient !== null && <ReportOptions defaultClient={autoClient} onApply={setOpts} />}
        {error && <div className="text-[var(--tt-red)] font-semibold">{error}</div>}
        {data && <ReportView report={data} />}
      </div>
    </div>
  );
}
