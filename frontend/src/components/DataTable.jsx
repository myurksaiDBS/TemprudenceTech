import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { show } from "@/lib/api";

export const DataTable = ({ headers, rows, searchable, testid, empty = "None recorded.", mono = [] }) => {
  const [q, setQ] = useState("");
  const filtered = useMemo(() => {
    if (!q) return rows;
    const s = q.toLowerCase();
    return rows.filter((r) => r.some((c) => typeof c !== "object" && String(c ?? "").toLowerCase().includes(s)));
  }, [rows, q]);
  return (
    <div data-testid={testid}>
      {searchable && (
        <div className="relative mb-3 max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--tt-muted)]" />
          <input
            data-testid={`${testid}-search`}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Filter rows..."
            className="w-full pl-9 pr-3 py-2 text-sm border border-[var(--tt-line)] rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-[var(--tt-blue)]/30"
          />
        </div>
      )}
      <div className="tt-card overflow-auto max-h-[640px]">
        <table className="tt-table w-full border-collapse">
          <thead>
            <tr>{headers.map((h) => <th key={h}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={headers.length} className="text-[var(--tt-muted)] italic">{empty}</td></tr>
            )}
            {filtered.map((r, i) => (
              <tr key={i}>
                {r.map((c, j) => (
                  <td key={j} className={mono.includes(j) ? "mono text-[12px]" : ""}>
                    {c !== null && typeof c === "object" ? c : show(c)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {searchable && <div className="text-xs text-[var(--tt-muted)] mt-2">{filtered.length} of {rows.length} rows</div>}
    </div>
  );
};

export const KV = ({ rows, testid, cols = 2 }) => (
  <dl data-testid={testid} className={`grid gap-x-8 gap-y-0 ${cols === 2 ? "md:grid-cols-2" : ""}`}>
    {rows.map(([k, v]) => (
      <div key={k} className="flex justify-between gap-4 py-2 border-b border-[var(--tt-line)]">
        <dt className="text-xs font-semibold text-[var(--tt-muted)] uppercase tracking-wide pt-0.5">{k}</dt>
        <dd className="text-sm text-right text-[var(--tt-navy)] font-medium break-all">{v !== null && typeof v === "object" ? v : show(v)}</dd>
      </div>
    ))}
  </dl>
);

export const Section = ({ title, children, action, testid }) => (
  <section className="tt-card p-6 tt-rise" data-testid={testid}>
    <div className="flex items-center justify-between mb-4">
      <h3 className="text-base font-bold text-[var(--tt-blue)]">{title}</h3>
      {action}
    </div>
    {children}
  </section>
);

export const PageHeader = ({ eyebrow, title, children, testid }) => (
  <div className="no-print px-10 pt-9 pb-6 flex flex-wrap items-end justify-between gap-4 border-b border-[var(--tt-line)] bg-white">
    <div>
      {eyebrow && <div className="tt-eyebrow mb-1">{eyebrow}</div>}
      <h1 data-testid={testid} className="text-3xl lg:text-4xl font-bold text-[var(--tt-navy)] tracking-tight">{title}</h1>
    </div>
    <div className="flex flex-wrap gap-2">{children}</div>
  </div>
);
