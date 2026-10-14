import { DataTable, KV, Section } from "@/components/DataTable";
import { BoolBadge } from "@/components/Status";
import { show } from "@/lib/api";

const Speed = ({ label, value, unit }) => (
  <div className="tt-card p-5">
    <div className="tt-eyebrow">{label}</div>
    <div className="text-3xl font-bold text-[var(--tt-navy)] mt-2">{value ?? "-"} <span className="text-sm font-semibold text-[var(--tt-muted)]">{value != null ? unit : ""}</span></div>
  </div>
);

export const NetworkTab = ({ d }) => {
  const n = d.network || {}, sp = d.speed || {}, wifi = n.wifi, px = n.proxy || {};
  return (
    <div className="space-y-6" data-testid="network-tab">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4" data-testid="throughput-cards">
        <Speed label="Download" value={sp.download_mbps} unit="Mbps" />
        <Speed label="Upload" value={sp.upload_mbps} unit="Mbps" />
        <Speed label="Latency (avg)" value={sp.latency_ms} unit="ms" />
      </div>
      <p className="text-xs text-[var(--tt-muted)] -mt-3">Throughput is measured between this PC and the Temprudence console{sp.error ? ` · ${sp.error}` : ""}.</p>
      <Section title="Network adapters">
        <DataTable testid="adapters-table" mono={[2, 3, 4, 5]}
          headers={["Adapter", "Status", "MAC", "IPv4 / subnet", "Gateway", "DNS", "DHCP", "Link speed"]}
          rows={(n.adapters || []).map((a) => [
            <div><div className="font-semibold">{a.name}</div><div className="text-[11px] text-[var(--tt-muted)]">{a.description}</div></div>,
            a.status, a.mac, (a.ipv4 || []).map((ip, i) => `${ip}/${(a.subnet || [])[i] || ""}`).join(" "), show(a.gateway), show(a.dns), a.dhcp, a.link_speed])} />
      </Section>
      <div className="grid xl:grid-cols-2 gap-6">
        <Section title="Wi-Fi">
          {wifi ? <KV cols={1} rows={Object.entries(wifi).map(([k, v]) => [k.replace(/_/g, " "), v])} /> : <p className="text-sm text-[var(--tt-muted)]">No wireless connection detected.</p>}
        </Section>
        <div className="space-y-6">
          <Section title="Firewall profiles">
            <DataTable testid="firewall-table" headers={["Profile", "Enabled", "Inbound", "Outbound"]}
              rows={(n.firewall || []).map((f) => [f.profile, <BoolBadge value={f.enabled} yes="On" no="Off" />, f.inbound, f.outbound])} />
          </Section>
          <Section title="Proxy">
            <KV cols={1} rows={[["User proxy", <BoolBadge value={px.enabled} yes="Enabled" no="Not set" goodWhen={false} />], ["Server", px.server],
              ["Auto-config URL", px.auto_config_url], ["WinHTTP", px.winhttp]]} />
          </Section>
        </div>
      </div>
    </div>
  );
};
