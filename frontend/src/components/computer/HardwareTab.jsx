import { DataTable, KV, Section } from "@/components/DataTable";
import { fmtDate } from "@/lib/api";

const Bar = ({ size, free }) => {
  const used = size ? Math.round(((size - free) / size) * 100) : 0;
  const low = size && (free / size < 0.15 || free < 10);
  return (
    <div className="min-w-[140px]">
      <div className="h-2 bg-[#eef3f8] rounded"><div className={`h-2 rounded ${low ? "bg-[var(--tt-red)]" : "bg-[var(--tt-blue)]"}`} style={{ width: `${used}%` }} /></div>
      <div className={`text-[11px] mt-1 ${low ? "text-[var(--tt-red)] font-bold" : "text-[var(--tt-muted)]"}`}>{used}% used{low ? " - low space" : ""}</div>
    </div>
  );
};

export const HardwareTab = ({ d }) => {
  const sy = d.system || {}, hw = d.hardware || {};
  return (
    <div className="space-y-6" data-testid="hardware-tab">
      <Section title="System">
        <KV rows={[["Manufacturer", sy.manufacturer], ["Model", sy.model], ["Serial number", <span className="mono">{sy.serial}</span>],
          ["System type", sy.system_type], ["BIOS", `${sy.bios_vendor || ""} ${sy.bios_version || ""}`], ["BIOS date", fmtDate(sy.bios_date)],
          ["Total memory", hw.memory_total_gb != null ? `${hw.memory_total_gb} GB` : "-"], ["UUID", <span className="mono text-xs">{sy.uuid}</span>]]} />
      </Section>
      <Section title="Processors">
        <DataTable testid="cpu-table" headers={["Processor", "Cores", "Logical", "Max clock (MHz)", "Socket"]}
          rows={(hw.cpu || []).map((c) => [c.name, c.cores, c.logical, c.max_clock_mhz, c.socket])} />
      </Section>
      <div className="grid xl:grid-cols-2 gap-6">
        <Section title="Memory modules">
          <DataTable testid="memory-table" headers={["Slot", "GB", "MHz", "Manufacturer", "Part number"]} mono={[4]}
            rows={(hw.memory_modules || []).map((m) => [m.slot, m.capacity_gb, m.speed_mhz, m.manufacturer, m.part_number])} />
        </Section>
        <Section title="Graphics">
          <DataTable testid="gpu-table" headers={["Adapter", "Driver", "VRAM (MB)", "Resolution"]}
            rows={(hw.gpu || []).map((g) => [g.name, g.driver_version, g.vram_mb, g.resolution])} />
        </Section>
      </div>
      <Section title="Volumes">
        <DataTable testid="volumes-table" headers={["Drive", "Label", "File system", "Size (GB)", "Free (GB)", "Usage"]}
          rows={(hw.volumes || []).map((v) => [v.device, v.label, v.filesystem, v.size_gb, v.free_gb, <Bar size={v.size_gb} free={v.free_gb} />])} />
      </Section>
      <Section title="Physical disks">
        <DataTable testid="disks-table" headers={["Model", "Interface", "Media", "Size (GB)", "Serial"]} mono={[4]}
          rows={(hw.physical_disks || []).map((p) => [p.model, p.interface, p.media_type, p.size_gb, p.serial])} />
      </Section>
      {(hw.battery || []).length > 0 && (
        <Section title="Battery">
          <DataTable testid="battery-table" headers={["Battery", "Charge %", "Status"]} rows={hw.battery.map((b) => [b.name, b.charge_pct, b.status])} />
        </Section>
      )}
    </div>
  );
};
