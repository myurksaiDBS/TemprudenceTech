import { AlertTriangle, CheckCircle2, Info, ShieldAlert, XCircle } from "lucide-react";

const STATUS = {
  critical: { label: "Critical", icon: ShieldAlert, cls: "bg-[#fbeae5] text-[var(--tt-red)] border-[#efc4b7]" },
  warning: { label: "Warning", icon: AlertTriangle, cls: "bg-[#fff6e0] text-[#8a5a00] border-[#f0d89a]" },
  ok: { label: "Healthy", icon: CheckCircle2, cls: "bg-[#e7f3ec] text-[#1e6b3d] border-[#bfdcc9]" },
};

export const StatusBadge = ({ status, testid }) => {
  const s = STATUS[status] || STATUS.ok;
  const Icon = s.icon;
  return (
    <span data-testid={testid} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-semibold ${s.cls}`}>
      <Icon size={13} /> {s.label}
    </span>
  );
};

const SEV = {
  high: { label: "High", icon: ShieldAlert, cls: "text-[var(--tt-red)] bg-[#fbeae5] border-[#efc4b7]" },
  medium: { label: "Medium", icon: AlertTriangle, cls: "text-[#8a5a00] bg-[#fff6e0] border-[#f0d89a]" },
  low: { label: "Low", icon: Info, cls: "text-[var(--tt-blue)] bg-[#e8f0f7] border-[#c3d5e6]" },
};

export const SeverityBadge = ({ severity }) => {
  const s = SEV[severity] || SEV.low;
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-bold uppercase tracking-wide ${s.cls}`}>
      <Icon size={12} /> {s.label}
    </span>
  );
};

export const BoolBadge = ({ value, yes = "Yes", no = "No", goodWhen = true }) => {
  if (value === null || value === undefined) return <span className="text-[var(--tt-muted)]">Unknown</span>;
  const good = value === goodWhen;
  const Icon = good ? CheckCircle2 : XCircle;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold ${good ? "text-[#1e6b3d]" : "text-[var(--tt-red)]"}`}>
      <Icon size={13} /> {value ? yes : no}
    </span>
  );
};
