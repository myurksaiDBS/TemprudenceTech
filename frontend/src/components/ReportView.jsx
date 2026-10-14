import { show } from "@/lib/api";

const CONFIDENTIAL =
  "CONFIDENTIAL - This report contains sensitive system and security information prepared by Temprudence Technologies for the named client. Do not distribute without authorization.";

const Block = ({ b }) => {
  if (b.type === "h1") return <h2 className="text-xl font-bold text-[var(--tt-blue)] mt-10 mb-3 pb-2 border-b-2 border-[var(--tt-blue)]">{b.text}</h2>;
  if (b.type === "h2") return <h3 className="text-base font-bold text-[var(--tt-navy)] mt-6 mb-2">{b.text}</h3>;
  if (b.type === "p") return <p className="text-sm text-[var(--tt-ink)] my-2">{b.text}</p>;
  if (b.type === "kv")
    return (
      <table className="w-full border-collapse text-sm my-2">
        <tbody>
          {b.rows.map(([k, v], i) => (
            <tr key={i}>
              <td className="w-1/3 bg-[#eef3f8] border border-[#c9d4de] px-3 py-1.5 font-semibold text-[var(--tt-navy)]">{k}</td>
              <td className="border border-[#c9d4de] px-3 py-1.5 break-all">{show(v)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  if (!b.rows.length) return <p className="text-sm italic text-[var(--tt-muted)] my-2">None recorded.</p>;
  return (
    <div className="overflow-x-auto my-2">
      <table className="tt-table w-full border-collapse border border-[#c9d4de]">
        <thead><tr>{b.headers.map((h) => <th key={h} style={{ position: "static" }}>{h}</th>)}</tr></thead>
        <tbody>
          {b.rows.map((r, i) => (
            <tr key={i} className={i % 2 ? "bg-[#f5f8fb]" : ""}>{r.map((c, j) => <td key={j} className="break-words">{show(c)}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export const ReportView = ({ report }) => (
  <article className="tt-card print-plain max-w-[980px] mx-auto bg-white px-14 py-12 shadow-sm" data-testid="report-view">
    <header className="text-center pb-10 border-b border-[var(--tt-line)]">
      <img src="/brand/logo.png" alt="Temprudence Technologies" className="w-[240px] mx-auto" />
      <h1 className="text-4xl font-bold text-[var(--tt-blue)] mt-6" data-testid="report-title">{report.title}</h1>
      <div className="text-lg text-[var(--tt-navy)] mt-1" data-testid="report-subtitle">{report.subtitle}</div>
      <div className="max-w-md mx-auto mt-6 text-left">
        <Block b={{ type: "kv", rows: report.meta }} />
      </div>
      <p className="text-xs font-bold text-[var(--tt-red)] mt-6 max-w-xl mx-auto">{CONFIDENTIAL}</p>
      <p className="text-sm text-[var(--tt-muted)] mt-2">A Division of YFI Enterprises, LLC</p>
    </header>
    {report.blocks.map((b, i) => <Block key={i} b={b} />)}
  </article>
);
