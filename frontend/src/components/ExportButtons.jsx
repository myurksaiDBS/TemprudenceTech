import { useState } from "react";
import { Download, Loader2, Printer } from "lucide-react";
import { toast } from "sonner";
import { downloadFile, errMsg } from "@/lib/api";

const FORMATS = [
  { id: "docx", label: "Word" },
  { id: "odt", label: "ODT" },
  { id: "pdf", label: "PDF" },
];

export const ExportButtons = ({ path, params = {}, name, showPrint }) => {
  const [busy, setBusy] = useState(null);
  const go = async (fmt) => {
    setBusy(fmt);
    try {
      await downloadFile(path, { ...params, format: fmt }, `${name}.${fmt}`);
      toast.success(`${fmt.toUpperCase()} report downloaded`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };
  return (
    <div className="flex flex-wrap items-center gap-2">
      {FORMATS.map((f) => (
        <button
          key={f.id}
          data-testid={`export-${f.id}-btn`}
          disabled={!!busy}
          onClick={() => go(f.id)}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md text-sm font-semibold border border-[var(--tt-blue)] text-[var(--tt-blue)] bg-white hover:bg-[var(--tt-blue)] hover:text-white transition-colors disabled:opacity-60"
        >
          {busy === f.id ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />} {f.label}
        </button>
      ))}
      {showPrint && (
        <button
          data-testid="print-report-btn"
          onClick={() => window.print()}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-md text-sm font-semibold text-[var(--tt-muted)] hover:text-[var(--tt-navy)] transition-colors"
        >
          <Printer size={15} /> Print
        </button>
      )}
    </div>
  );
};
