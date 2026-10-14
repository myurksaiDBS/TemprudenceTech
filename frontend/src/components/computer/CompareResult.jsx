import { Minus, Plus, RefreshCw } from "lucide-react";
import { DataTable, Section } from "@/components/DataTable";
import { fmtDate, show } from "@/lib/api";

const Count = ({ icon: Icon, n, label, cls }) => (
  <div className={`tt-card px-4 py-3 flex items-center gap-3 ${cls}`}>
    <Icon size={18} /><div><div className="text-2xl font-bold">{n}</div><div className="text-xs font-semibold">{label}</div></div>
  </div>
);

const Changes = ({ title, rows, testid }) => (
  <Section title={title} testid={testid}>
    {rows.length === 0 ? <p className="text-sm text-[var(--tt-muted)]">No changes.</p> :
      <DataTable headers={["Field", "Before", "After"]} rows={rows.map((r) => [r.field, show(r.from), show(r.to)])} />}
  </Section>
);

export const CompareResult = ({ diff }) => {
  const { software: sw, os, hardware, network, users } = diff.diff;
  return (
    <div className="space-y-6" data-testid="compare-result">
      <div className="tt-card p-5 bg-[var(--tt-navy)] text-white">
        <div className="tt-eyebrow !text-white/60">Comparison</div>
        <div className="text-lg font-bold mt-1">{fmtDate(diff.from.scanned_at)} → {fmtDate(diff.to.scanned_at)}</div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Count icon={Plus} n={sw.added.length} label="Apps added" cls="text-[#1e6b3d]" />
        <Count icon={Minus} n={sw.removed.length} label="Apps removed" cls="text-[var(--tt-red)]" />
        <Count icon={RefreshCw} n={sw.updated.length} label="Apps updated" cls="text-[var(--tt-blue)]" />
      </div>
      <Section title="Software changes" testid="compare-software">
        <DataTable headers={["Change", "Application", "Before", "After"]} empty="No software changes." rows={[
          ...sw.added.map((a) => ["Added", a.name, "-", a.version]),
          ...sw.removed.map((a) => ["Removed", a.name, a.version, "-"]),
          ...sw.updated.map((a) => ["Updated", a.name, a.from, a.to]),
        ]} />
      </Section>
      <Section title="User & privilege changes" testid="compare-users">
        {users.length === 0 ? <p className="text-sm text-[var(--tt-muted)]">No changes.</p> :
          <DataTable headers={["Account", "Change"]} rows={users.map((u) => [u.user, u.change])} />}
      </Section>
      <div className="grid xl:grid-cols-3 gap-6">
        <Changes title="Operating system" rows={os} testid="compare-os" />
        <Changes title="Hardware" rows={hardware} testid="compare-hardware" />
        <Changes title="Network" rows={network} testid="compare-network" />
      </div>
    </div>
  );
};
