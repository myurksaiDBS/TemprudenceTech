import { ShieldCheck } from "lucide-react";
import { DataTable, KV, Section } from "@/components/DataTable";
import { BoolBadge } from "@/components/Status";
import { fmtDate } from "@/lib/api";

export const UsersTab = ({ d }) => {
  const u = d.users || {};
  const local = u.local || [];
  const admins = local.filter((x) => x.is_admin && x.enabled);
  return (
    <div className="space-y-6" data-testid="users-tab">
      <Section title="Summary">
        <KV rows={[["Signed-in user", u.current_user || d.system?.current_user], ["Local accounts", local.length],
          ["Enabled local administrators", admins.map((a) => a.name).join(", ") || "None"], ["Administrators group", u.admin_group]]} />
        {(u.sessions || []).length > 0 && (
          <div className="mt-4"><div className="tt-eyebrow mb-1">Active sessions</div>
            {u.sessions.map((s, i) => <div key={i} className="mono text-xs text-[var(--tt-navy)]">{s}</div>)}</div>
        )}
      </Section>
      <Section title={`Local accounts (${local.length})`}>
        <DataTable testid="local-users-table" headers={["Account", "Enabled", "Role", "Last logon", "Password required", "Password last set", "Groups"]}
          rows={local.map((x) => [
            <div><div className="font-semibold">{x.name}</div>{x.full_name && <div className="text-[11px] text-[var(--tt-muted)]">{x.full_name}</div>}</div>,
            <BoolBadge value={x.enabled} yes="Enabled" no="Disabled" />,
            x.is_admin ? <span className="inline-flex items-center gap-1 text-xs font-bold text-[var(--tt-red)]"><ShieldCheck size={13} /> Administrator</span> : "Standard user",
            fmtDate(x.last_logon), x.password_required, fmtDate(x.password_last_set), (x.groups || []).join(", ")])} />
      </Section>
      <Section title="Group memberships">
        <DataTable testid="groups-table" headers={["Group", "Description", "Members"]}
          rows={(u.groups || []).filter((g) => (g.members || []).length).map((g) => [
            <span className={g.is_admin_group ? "font-bold text-[var(--tt-red)]" : "font-semibold"}>{g.name}</span>, g.description,
            (g.members || []).map((m) => m.name).join(", ")])} />
      </Section>
    </div>
  );
};
