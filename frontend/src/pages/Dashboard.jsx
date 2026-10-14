import { Link } from "react-router-dom";
import { HardDrive, Monitor, ScanLine, ShieldAlert, ShieldOff, UserCog, Clock, Bell, CalendarClock } from "lucide-react";
import { useApi } from "@/hooks/useApi";
import { fmtDate } from "@/lib/api";
import { PageHeader, Section } from "@/components/DataTable";
import { SeverityBadge } from "@/components/Status";

const Stat = ({ label, value, icon: Icon, tone = "blue", testid, delay }) => (
  <div className="tt-card p-5 tt-rise" style={{ animationDelay: `${delay}ms` }} data-testid={testid}>
    <div className="flex items-center justify-between">
      <span className="tt-eyebrow">{label}</span>
      <Icon size={18} className={tone === "red" ? "text-[var(--tt-red)]" : "text-[var(--tt-blue)]"} />
    </div>
    <div className={`text-4xl font-bold mt-3 ${tone === "red" ? "text-[var(--tt-red)]" : "text-[var(--tt-navy)]"}`}>{value}</div>
  </div>
);

export default function Dashboard() {
  const { data, loading } = useApi("/dashboard");
  if (loading || !data) return <PageHeader eyebrow="Overview" title="Fleet dashboard" testid="dashboard-title" />;
  const t = data.totals, f = data.flag_counts;
  const max = Math.max(1, ...data.os_distribution.map((o) => o.count));
  return (
    <div>
      <PageHeader eyebrow="Overview" title="Fleet dashboard" testid="dashboard-title">
        <Link to="/scan" data-testid="dashboard-scan-btn" className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-[var(--tt-red)] text-white text-sm font-bold hover:bg-[#962810] transition-colors">
          <ScanLine size={16} /> Scan a computer
        </Link>
      </PageHeader>
      <div className="px-10 py-8 space-y-8">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Stat label="Computers" value={t.computers} icon={Monitor} testid="stat-computers" delay={0} />
          <Stat label="Total scans" value={t.scans} icon={ScanLine} testid="stat-scans" delay={60} />
          <Stat label="Critical" value={t.critical} icon={ShieldAlert} tone="red" testid="stat-critical" delay={120} />
          <Stat label="Applications tracked" value={t.applications} icon={HardDrive} testid="stat-apps" delay={180} />
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Stat label="Extra administrators" value={f.extra_admins} icon={UserCog} testid="flag-extra-admins" delay={200} />
          <Stat label="Security disabled" value={f.security} icon={ShieldOff} tone={f.security ? "red" : "blue"} testid="flag-security" delay={240} />
          <Stat label="Low disk space" value={f.low_disk} icon={HardDrive} testid="flag-low-disk" delay={280} />
          <Stat label="Old / unsupported OS" value={f.old_os} icon={Clock} tone={f.old_os ? "red" : "blue"} testid="flag-old-os" delay={320} />
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Link to="/alerts" className="block" data-testid="stat-open-alerts-link">
            <Stat label="Open change alerts" value={data.open_alerts} icon={Bell} tone={data.open_alerts ? "red" : "blue"} testid="stat-open-alerts" delay={340} />
          </Link>
          <Stat label="Weekly rescans on" value={data.scheduled} icon={CalendarClock} testid="stat-scheduled" delay={360} />
          <Stat label="Overdue rescans" value={data.overdue} icon={Clock} tone={data.overdue ? "red" : "blue"} testid="stat-overdue" delay={380} />
        </div>
        <div className="grid lg:grid-cols-[1.4fr_1fr] gap-6">
          <Section title="Flagged items" testid="flagged-items">
            {data.flagged.length === 0 && <p className="text-sm text-[var(--tt-muted)]">No flagged items. Every scanned computer looks healthy.</p>}
            <ul className="divide-y divide-[var(--tt-line)]">
              {data.flagged.map((x, i) => (
                <li key={i} className="py-3 flex items-start gap-3" data-testid={`flagged-item-${i}`}>
                  <SeverityBadge severity={x.severity} />
                  <div className="min-w-0">
                    <Link to={`/computers/${x.computer_id}`} className="font-semibold text-[var(--tt-blue)] hover:underline text-sm">{x.computer_name}</Link>
                    <span className="text-sm text-[var(--tt-navy)]"> — {x.title}</span>
                    {x.detail && <div className="text-xs text-[var(--tt-muted)] mt-0.5 truncate">{x.detail}</div>}
                  </div>
                </li>
              ))}
            </ul>
          </Section>
          <div className="space-y-6">
            <Section title="Operating systems" testid="os-distribution">
              {data.os_distribution.length === 0 && <p className="text-sm text-[var(--tt-muted)]">No scans yet.</p>}
              {data.os_distribution.map((o) => (
                <div key={o.name} className="mb-3">
                  <div className="flex justify-between text-sm"><span className="font-medium">{o.name}</span><span className="mono">{o.count}</span></div>
                  <div className="h-2 bg-[#eef3f8] rounded mt-1"><div className="h-2 rounded bg-[var(--tt-blue)]" style={{ width: `${(o.count / max) * 100}%` }} /></div>
                </div>
              ))}
            </Section>
            <Section title="Recent scans" testid="recent-scans">
              {data.recent_scans.length === 0 && <p className="text-sm text-[var(--tt-muted)]">No scans yet. Download the scanner to get started.</p>}
              <ul className="divide-y divide-[var(--tt-line)]">
                {data.recent_scans.map((s) => (
                  <li key={s.id} className="py-2.5 flex justify-between gap-3 text-sm">
                    <Link to={`/computers/${s.computer_id}`} className="font-semibold text-[var(--tt-blue)] hover:underline">{s.summary?.computer_name}</Link>
                    <span className="text-[var(--tt-muted)] text-xs pt-0.5">{fmtDate(s.scanned_at)} · {s.flag_count} flags</span>
                  </li>
                ))}
              </ul>
            </Section>
          </div>
        </div>
      </div>
    </div>
  );
}
