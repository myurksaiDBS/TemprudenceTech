import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { fmtDate, show } from "@/lib/api";
import { PageHeader } from "@/components/DataTable";
import { StatusBadge } from "@/components/Status";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function Computers() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [osName, setOsName] = useState("all");
  const nav = useNavigate();
  const { data, loading } = useApi("/computers", { q, status: status === "all" ? "" : status, os_name: osName === "all" ? "" : osName });
  const rows = data || [];
  return (
    <div>
      <PageHeader eyebrow="Fleet" title="Computers" testid="computers-title">
        <Link to="/scan" className="inline-flex items-center px-4 py-2.5 rounded-md bg-[var(--tt-red)] text-white text-sm font-bold hover:bg-[#962810] transition-colors" data-testid="computers-scan-btn">
          Scan a computer
        </Link>
      </PageHeader>
      <div className="px-10 py-8">
        <div className="flex flex-wrap gap-3 mb-5">
          <div className="relative flex-1 min-w-[260px] max-w-md">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--tt-muted)]" />
            <input
              data-testid="computers-search-input" value={q} onChange={(e) => setQ(e.target.value)}
              placeholder="Search name, serial, owner, IP, model..."
              className="w-full pl-9 pr-3 py-2.5 text-sm border border-[var(--tt-line)] rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-[var(--tt-blue)]/30"
            />
          </div>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-[170px] bg-white" data-testid="status-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="warning">Warning</SelectItem>
              <SelectItem value="ok">Healthy</SelectItem>
            </SelectContent>
          </Select>
          <Select value={osName} onValueChange={setOsName}>
            <SelectTrigger className="w-[170px] bg-white" data-testid="os-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All operating systems</SelectItem>
              <SelectItem value="Windows 11">Windows 11</SelectItem>
              <SelectItem value="Windows 10">Windows 10</SelectItem>
              <SelectItem value="Server">Windows Server</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="tt-card overflow-auto">
          <table className="tt-table w-full border-collapse" data-testid="computers-table">
            <thead>
              <tr><th>Computer</th><th>Operating system</th><th>Owner</th><th>Model</th><th>IP</th><th>Apps</th><th>Last scan</th><th>Status</th></tr>
            </thead>
            <tbody>
              {!loading && rows.length === 0 && (
                <tr><td colSpan={8} className="italic text-[var(--tt-muted)] py-6">No computers found. Run the scanner on a Windows PC to add one.</td></tr>
              )}
              {rows.map((c) => (
                <tr key={c.id} className="cursor-pointer" onClick={() => nav(`/computers/${c.id}`)} data-testid={`computer-row-${c.name}`}>
                  <td>
                    <div className="font-bold text-[var(--tt-blue)]">{c.name}</div>
                    <div className="mono text-[11px] text-[var(--tt-muted)]">{show(c.serial)}</div>
                  </td>
                  <td>{show(c.summary?.os_caption)} <span className="text-[var(--tt-muted)]">{show(c.summary?.os_version)}</span></td>
                  <td>{show(c.owner)}</td>
                  <td>{show(c.summary?.manufacturer)} {show(c.summary?.model)}</td>
                  <td className="mono text-[12px]">{show(c.summary?.ip)}</td>
                  <td>{show(c.summary?.software_count)}</td>
                  <td className="whitespace-nowrap">{fmtDate(c.last_scan_at)}</td>
                  <td><StatusBadge status={c.status} testid={`computer-status-${c.name}`} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="text-xs text-[var(--tt-muted)] mt-3" data-testid="computers-count">{rows.length} computer{rows.length === 1 ? "" : "s"}</div>
      </div>
    </div>
  );
}
