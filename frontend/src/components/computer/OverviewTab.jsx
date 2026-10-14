import { fmtDate } from "@/lib/api";
import { KV, Section } from "@/components/DataTable";
import { BoolBadge, SeverityBadge } from "@/components/Status";

export const OverviewTab = ({ d, flags }) => {
  const os = d.os || {}, sy = d.system || {}, sec = d.security || {}, sp = d.speed || {};
  const av = sec.antivirus || [];
  const osDrive = (sec.bitlocker || []).find((b) => String(b.mount || "").toUpperCase().startsWith("C"));
  return (
    <div className="grid xl:grid-cols-2 gap-6" data-testid="overview-tab">
      <Section title={`Flagged items (${flags.length})`} testid="overview-flags">
        {flags.length === 0 && <p className="text-sm text-[var(--tt-muted)]">No issues flagged in this scan.</p>}
        <ul className="divide-y divide-[var(--tt-line)]">
          {flags.map((f, i) => (
            <li key={i} className="py-2.5 flex gap-3 items-start">
              <SeverityBadge severity={f.severity} />
              <div><div className="text-sm font-semibold text-[var(--tt-navy)]">{f.title}</div><div className="text-xs text-[var(--tt-muted)]">{f.category} · {f.detail}</div></div>
            </li>
          ))}
        </ul>
      </Section>
      <Section title="Operating system" testid="overview-os">
        <KV cols={1} rows={[["Edition", os.caption], ["Version", os.display_version], ["Build", <span className="mono">{os.build}</span>],
          ["Architecture", os.architecture], ["Installed", fmtDate(os.install_date)], ["Last boot", fmtDate(os.last_boot)],
          ["Activation", os.activation_status], ["Updates installed", (os.hotfixes || []).length]]} />
      </Section>
      <Section title="Security & settings" testid="overview-security">
        <KV cols={1} rows={[
          ["UAC", <BoolBadge value={sec.uac_enabled} yes="Enabled" no="Disabled" />],
          ["BitLocker (OS drive)", osDrive ? <BoolBadge value={String(osDrive.protection).toLowerCase() === "on"} yes="Protected" no={`Off (${osDrive.status})`} /> : "Not collected"],
          ["Antivirus", av.length ? av.map((a) => `${a.name}${a.enabled ? "" : " (off)"}`).join(", ") : sec.defender ? "Microsoft Defender" : "-"],
          ["Defender real-time", <BoolBadge value={sec.defender?.realtime} yes="On" no="Off" />],
          ["Secure Boot", <BoolBadge value={sec.secure_boot} yes="On" no="Off" />],
          ["TPM", sec.tpm ? (sec.tpm.ready ? "Present, ready" : "Present, not ready") : "-"],
          ["Time zone", sy.timezone], ["Domain / workgroup", sy.domain], ["Domain joined", sy.part_of_domain],
        ]} />
      </Section>
      <Section title="System & throughput" testid="overview-system">
        <KV cols={1} rows={[["Signed-in user", sy.current_user], ["Scan ran as", sy.scan_user],
          ["Administrator scan", <BoolBadge value={d.is_admin} yes="Full scan" no="Limited" />],
          ["Latency to console", sp.latency_ms != null ? `${sp.latency_ms} ms` : "-"],
          ["Download", sp.download_mbps != null ? `${sp.download_mbps} Mbps` : "-"], ["Upload", sp.upload_mbps != null ? `${sp.upload_mbps} Mbps` : "-"],
          ["Scanner version", d.scanner_version]]} />
        {sp.error && <p className="text-xs text-[var(--tt-muted)] mt-3">Throughput note: {sp.error}</p>}
      </Section>
    </div>
  );
};
