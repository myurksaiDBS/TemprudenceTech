const RULES = [
  ["software_added", "Apps installed"],
  ["software_removed", "Apps removed"],
  ["accounts", "Account changes (added, removed, enabled, disabled, groups)"],
  ["admin_rights", "Administrator rights granted or removed"],
  ["security", "New security findings"],
];

export const AlertRulesForm = ({ value, onChange, disabled, prefix = "rules" }) => (
  <div className={disabled ? "opacity-50 pointer-events-none" : ""} data-testid={`${prefix}-form`}>
    <div className="space-y-2.5">
      {RULES.map(([k, label]) => (
        <label key={k} className="flex items-center gap-3 text-sm cursor-pointer">
          <input type="checkbox" checked={!!value[k]} onChange={(e) => onChange({ ...value, [k]: e.target.checked })}
            data-testid={`${prefix}-${k}`} className="accent-[var(--tt-blue)] w-4 h-4" />
          {label}
        </label>
      ))}
    </div>
    <label className="flex items-center gap-3 text-sm mt-4">
      <span className="font-semibold text-[var(--tt-navy)]">Minimum severity</span>
      <select value={value.min_severity} onChange={(e) => onChange({ ...value, min_severity: e.target.value })} data-testid={`${prefix}-min-severity`}
        className="px-3 py-1.5 text-sm border border-[var(--tt-line)] rounded-md bg-white">
        <option value="low">Low and above (all)</option>
        <option value="medium">Medium and above</option>
        <option value="high">High only</option>
      </select>
    </label>
    <p className="text-xs text-[var(--tt-muted)] mt-2">High: new accounts, admin rights granted, critical security findings. Medium: apps installed, other account changes. Low: apps removed.</p>
  </div>
);
