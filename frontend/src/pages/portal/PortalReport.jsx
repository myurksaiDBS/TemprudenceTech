import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { ReportView } from "@/components/ReportView";
import { ExportButtons } from "@/components/ExportButtons";

export default function PortalReport({ fleet }) {
  const { id } = useParams();
  const base = fleet ? "/portal/fleet" : `/portal/computers/${id}/report`;
  const { data, error } = useApi(`${base}/data`);
  return (
    <div className="px-6 py-8">
      <div className="no-print max-w-[980px] mx-auto flex flex-wrap items-center justify-between gap-3 mb-6">
        <Link to="/portal" data-testid="portal-back-btn" className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--tt-muted)] hover:text-[var(--tt-navy)]">
          <ArrowLeft size={15} /> Back to your computers
        </Link>
        <ExportButtons path={`${base}/export`} name={`Temprudence_${data?.subtitle || "Report"}`} showPrint />
      </div>
      {error && <div className="text-center text-[var(--tt-red)] font-semibold" data-testid="portal-report-error">{error}</div>}
      {data && <ReportView report={data} />}
    </div>
  );
}
