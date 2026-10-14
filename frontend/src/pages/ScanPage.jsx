import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CalendarClock, Check, Copy, Download, KeyRound, Loader2, MonitorDown, Upload } from "lucide-react";
import { toast } from "sonner";
import { useApi } from "@/hooks/useApi";
import { useAuth } from "@/context/AuthContext";
import { api, BACKEND, errMsg, fmtDate } from "@/lib/api";
import { PageHeader, Section } from "@/components/DataTable";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { KeysPanel } from "@/components/KeysPanel";

const StepItem = ({ n, title, children }) => (
  <li className="flex gap-4">
    <span className="w-8 h-8 shrink-0 rounded-full bg-[var(--tt-blue)] text-white font-bold flex items-center justify-center text-sm">{n}</span>
    <div className="pt-1"><div className="font-bold text-[var(--tt-navy)]">{title}</div><div className="text-sm text-[var(--tt-muted)] mt-1">{children}</div></div>
  </li>
);

export default function ScanPage() {
  const { user } = useAuth();
  const nav = useNavigate();
  const { data: keys, reload } = useApi("/keys");
  const active = (keys || []).filter((k) => k.active);
  const [keyId, setKeyId] = useState(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [weekly, setWeekly] = useState(false);
  const fileRef = useRef();
  const key = active.find((k) => k.id === keyId) || active[0];
  const scriptUrl = key ? `${BACKEND}/api/scanner/script.ps1?k=${key.key}${weekly ? "&schedule=1" : ""}` : "";
  const exeUrl = key ? `${BACKEND}/api/scanner/exe?k=${key.key}${weekly ? "&schedule=1" : ""}` : "";
  const oneLiner = key ? `powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol='Tls12'; iex (irm '${scriptUrl}')"` : "";

  const copy = async () => {
    await navigator.clipboard.writeText(oneLiner).catch(() => {});
    setCopied(true);
    toast.success("Command copied");
    setTimeout(() => setCopied(false), 1800);
  };
  const importFile = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true);
    const fd = new FormData();
    fd.append("file", f);
    try {
      const r = await api.post("/scans/import", fd);
      toast.success(`Imported scan for ${r.data.computer_name}`);
      nav(`/computers/${r.data.computer_id}`);
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); e.target.value = ""; }
  };

  return (
    <div>
      <PageHeader eyebrow="Collect inventory" title="Scan a computer" testid="scan-title" />
      <div className="px-10 py-8 grid xl:grid-cols-[1.35fr_1fr] gap-6">
        <div className="space-y-6">
          <Section title="Windows scanner" testid="ps-scanner-section">
            {!key ? <p className="text-sm text-[var(--tt-red)] font-semibold">No active upload key. {user?.role === "admin" ? "Create one below." : "Ask an administrator to create one."}</p> : (
              <>
                <div className="flex flex-wrap items-center gap-3 mb-5">
                  <KeyRound size={16} className="text-[var(--tt-blue)]" />
                  <span className="text-sm font-semibold">Upload key</span>
                  <Select value={key.id} onValueChange={setKeyId}>
                    <SelectTrigger className="w-[240px] bg-white" data-testid="scan-key-select"><SelectValue /></SelectTrigger>
                    <SelectContent>{active.map((k) => <SelectItem key={k.id} value={k.id}>{k.label}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <label className="flex items-start gap-3 mb-5 p-3 rounded-md bg-[#eef3f8] cursor-pointer" data-testid="schedule-weekly-label">
                  <input type="checkbox" checked={weekly} onChange={(e) => setWeekly(e.target.checked)} data-testid="schedule-weekly-checkbox" className="accent-[var(--tt-blue)] w-4 h-4 mt-0.5" />
                  <span>
                    <span className="flex items-center gap-1.5 text-sm font-bold text-[var(--tt-navy)]"><CalendarClock size={15} /> Schedule weekly rescans</span>
                    <span className="block text-xs text-[var(--tt-muted)] mt-0.5">Adds a Windows scheduled task (Mondays 9:00 AM, runs as SYSTEM) that rescans and uploads automatically. Change alerts appear on the Alerts page.</span>
                  </span>
                </label>
                <div className="tt-eyebrow mb-2">Easiest: double-click Windows scanner</div>
                <div className="flex flex-wrap gap-3 mb-2">
                  <a href={exeUrl} data-testid="download-exe-btn"
                    className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-[var(--tt-red)] text-white text-sm font-bold hover:bg-[#962810] transition-colors">
                    <MonitorDown size={16} /> Download {weekly ? "TemprudenceScanner_Weekly.exe" : "TemprudenceScanner.exe"}
                  </a>
                </div>
                <p className="text-xs text-[var(--tt-muted)] mb-6">Double-click and approve the Administrator prompt. The file isn't code-signed yet, so Windows SmartScreen may warn you. Choose “More info”, then “Run anyway”. Requires PowerShell 5.1, which is built into Windows 10, Windows 11 and Server 2016 or later.</p>
                <div className="tt-eyebrow mb-2">Or: one-line command (run in PowerShell as Administrator)</div>
                <div className="relative bg-[var(--tt-navy)] rounded-md p-4 pr-14">
                  <code className="mono text-[12px] text-[#cfe3f5] break-all block" data-testid="scan-one-liner">{oneLiner}</code>
                  <button onClick={copy} data-testid="copy-command-btn" className="absolute top-3 right-3 p-2 rounded bg-white/10 text-white hover:bg-white/20 transition-colors" aria-label="Copy command">
                    {copied ? <Check size={16} /> : <Copy size={16} />}
                  </button>
                </div>
                <div className="flex flex-wrap gap-3 mt-5">
                  <a href={`${scriptUrl}&download=1`} data-testid="download-script-btn"
                    className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md border border-[var(--tt-blue)] text-[var(--tt-blue)] text-sm font-bold hover:bg-[var(--tt-blue)] hover:text-white transition-colors">
                    <Download size={16} /> Download TemprudenceScanner.ps1
                  </a>
                </div>
                <p className="text-xs text-[var(--tt-muted)] mt-3">If you download the file, run: <span className="mono">powershell -ExecutionPolicy Bypass -File .\TemprudenceScanner.ps1</span></p>
                {weekly && <p className="text-xs text-[var(--tt-muted)] mt-1">To stop weekly rescans on a PC, run in an Administrator PowerShell: <span className="mono">Unregister-ScheduledTask -TaskName 'Temprudence Weekly Inventory' -Confirm:$false</span></p>}
              </>
            )}
          </Section>
          <Section title="How it works" testid="scan-steps">
            <ol className="space-y-5">
              <StepItem n={1} title="Run the scanner as Administrator">Double-click the .exe, or right-click Start, choose “Terminal (Admin)” and paste the command. Without admin rights, BitLocker, Secure Boot and TPM are marked as limited.</StepItem>
              <StepItem n={2} title="Let it run">The scanner collects OS, software, hardware, network, users and security settings, then runs a short throughput test. It takes about 1–2 minutes.</StepItem>
              <StepItem n={3} title="Results upload automatically">The PC appears in Computers. A copy is also saved in %TEMP% in case the upload fails.</StepItem>
            </ol>
          </Section>
        </div>
        <div className="space-y-6">
          <Section title="Import scan file" testid="import-section">
            <p className="text-sm text-[var(--tt-muted)] mb-4">For offline PCs: run with <span className="mono">$env:TT_NOUPLOAD='1'</span>, then import the saved Temprudence_Inventory_*.json file here.</p>
            <input ref={fileRef} type="file" accept=".json,application/json" className="hidden" onChange={importFile} data-testid="import-file-input" />
            <button onClick={() => fileRef.current?.click()} disabled={busy} data-testid="import-file-btn"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md border border-[var(--tt-blue)] text-[var(--tt-blue)] text-sm font-bold hover:bg-[var(--tt-blue)] hover:text-white transition-colors disabled:opacity-60">
              {busy ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />} Choose JSON file
            </button>
          </Section>
          <KeysPanel keys={keys || []} reload={reload} isAdmin={user?.role === "admin"} />
          <p className="text-xs text-[var(--tt-muted)]">Last key activity: {fmtDate(active[0]?.last_used)}</p>
        </div>
      </div>
    </div>
  );
}
