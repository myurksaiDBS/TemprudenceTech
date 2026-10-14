import { DataTable, Section } from "@/components/DataTable";
import { fmtDate } from "@/lib/api";

export const SoftwareTab = ({ d }) => {
  const sw = [...(d.software || [])].sort((a, b) => String(a.name).localeCompare(String(b.name)));
  const updates = d.os?.hotfixes || [];
  return (
    <div className="space-y-6" data-testid="software-tab">
      <Section title={`Installed applications (${sw.length})`}>
        <DataTable searchable testid="software-table" mono={[1]} headers={["Application", "Version", "Publisher", "Installed", "Type", "Size (MB)"]}
          rows={sw.map((s) => [s.name, s.version, s.publisher, s.install_date, s.arch, s.size_mb])} />
      </Section>
      <Section title={`Installed Windows updates (${updates.length})`}>
        <DataTable testid="updates-table" mono={[0]} headers={["Update", "Description", "Installed"]}
          rows={updates.map((h) => [h.id, h.description, fmtDate(h.installed_on)])} />
      </Section>
    </div>
  );
};
