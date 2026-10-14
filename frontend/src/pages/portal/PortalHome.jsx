import { Link, useOutletContext } from "react-router-dom";
import { FileText, Monitor } from "lucide-react";
import { fmtDate, show } from "@/lib/api";
import { StatusBadge } from "@/components/Status";
import { ExportButtons } from "@/components/ExportButtons";

export default function PortalHome() {
  const data = useOutletContext();
  const comps = data?.computers || [];
  return (
    <div className="max-w-[1280px] mx-auto px-8 py-10 space-y-8">
      <section className="rounded-md p-6 bg-[var(--tt-navy)] text-white tt-rise" data-testid="portal-fleet-card">
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div>
            <div className="tt-eyebrow !text-white/60">Your inventory</div>
            <h1 className="text-3xl lg:text-4xl font-bold mt-1">{data?.client?.name || "Client"} summary report</h1>
            <p className="text-white/70 text-sm mt-2">{comps.length} computer{comps.length === 1 ? "" : "s"} inventoried by Temprudence Technologies.</p>
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <Link to="/portal/summary" data-testid="portal-view-summary-btn"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-[var(--tt-red)] text-white text-sm font-bold hover:bg-[#962810] transition-colors">
              <FileText size={16} /> View summary report
            </Link>
            <div className="bg-white rounded-md p-1"><ExportButtons path="/portal/fleet/export" name="Temprudence_Summary" /></div>
          </div>
        </div>
      </section>
      <section className="tt-rise" style={{ animationDelay: "100ms" }}>
        <h2 className="text-lg font-bold text-[var(--tt-blue)] mb-3 flex items-center gap-2"><Monitor size={18} /> Your computers</h2>
        <div className="tt-card overflow-auto">
          <table className="tt-table w-full border-collapse" data-testid="portal-computers-table">
            <thead><tr><th>Computer</th><th>Site</th><th>Operating system</th><th>Model</th><th>Apps</th><th>Last inventory</th><th>Status</th><th>Report</th></tr></thead>
            <tbody>
              {comps.length === 0 && <tr><td colSpan={8} className="italic text-[var(--tt-muted)] py-6">No computers have been inventoried yet.</td></tr>}
              {comps.map((c) => (
                <tr key={c.id} data-testid={`portal-computer-row-${c.name}`}>
                  <td className="font-bold text-[var(--tt-blue)]">{c.name}</td>
                  <td>{show(c.site)}</td>
                  <td>{show(c.summary?.os_caption)} <span className="text-[var(--tt-muted)]">{show(c.summary?.os_version)}</span></td>
                  <td>{show(c.summary?.manufacturer)} {show(c.summary?.model)}</td>
                  <td>{show(c.summary?.software_count)}</td>
                  <td className="whitespace-nowrap">{fmtDate(c.last_scan_at)}</td>
                  <td><StatusBadge status={c.status} /></td>
                  <td><Link to={`/portal/computers/${c.id}`} data-testid={`portal-report-link-${c.name}`} className="text-sm font-bold text-[var(--tt-red)] hover:underline">View report</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
