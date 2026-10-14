import { useState } from "react";
import { GitCompare, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { useApi } from "@/hooks/useApi";
import { api, errMsg, fmtDate } from "@/lib/api";
import { Section } from "@/components/DataTable";
import { CompareResult } from "@/components/computer/CompareResult";

export const HistoryTab = ({ computerId, currentScanId, onView }) => {
  const { data } = useApi(`/computers/${computerId}/scans`);
  const [sel, setSel] = useState([]);
  const [diff, setDiff] = useState(null);
  const [busy, setBusy] = useState(false);
  const scans = data || [];
  const toggle = (id) => setSel((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id].slice(-2)));
  const compare = async () => {
    setBusy(true);
    try {
      const r = await api.get(`/computers/${computerId}/compare`, { params: { a: sel[0], b: sel[1] } });
      setDiff(r.data);
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-6" data-testid="history-tab">
      <Section title={`Scan history (${scans.length})`} action={
        <button onClick={compare} disabled={sel.length !== 2 || busy} data-testid="compare-scans-btn"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-[var(--tt-red)] text-white text-sm font-bold hover:bg-[#962810] transition-colors disabled:opacity-40">
          {busy ? <Loader2 size={15} className="animate-spin" /> : <GitCompare size={15} />} Compare selected ({sel.length}/2)
        </button>}>
        <div className="tt-card overflow-auto">
          <table className="tt-table w-full border-collapse" data-testid="scans-table">
            <thead><tr><th>Compare</th><th>Scanned</th><th>Source</th><th>OS build</th><th>Apps</th><th>Admins</th><th>Flags</th><th></th></tr></thead>
            <tbody>
              {scans.map((s, i) => (
                <tr key={s.id} data-testid={`scan-row-${i}`}>
                  <td><input type="checkbox" checked={sel.includes(s.id)} onChange={() => toggle(s.id)} data-testid={`scan-select-${i}`} className="accent-[var(--tt-blue)] w-4 h-4" /></td>
                  <td className="whitespace-nowrap font-semibold">{fmtDate(s.scanned_at)}{i === 0 && <span className="ml-2 text-[10px] uppercase font-bold text-[var(--tt-blue)]">Latest</span>}</td>
                  <td>{s.source}</td>
                  <td className="mono text-xs">{s.summary?.os_build}</td>
                  <td>{s.summary?.software_count}</td>
                  <td>{s.summary?.admin_count}</td>
                  <td>{(s.flags || []).length}</td>
                  <td>{s.id === currentScanId ? <span className="text-xs text-[var(--tt-muted)]">Viewing</span> :
                    <button onClick={() => onView(s.id)} data-testid={`scan-view-${i}`} className="text-xs font-bold text-[var(--tt-blue)] hover:underline">View</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-[var(--tt-muted)] mt-3">Select any two scans and choose Compare to see what changed.</p>
      </Section>
      {diff && <CompareResult diff={diff} />}
    </div>
  );
};
