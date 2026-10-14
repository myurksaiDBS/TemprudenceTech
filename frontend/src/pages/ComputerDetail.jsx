import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { FileText, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useApi } from "@/hooks/useApi";
import { useAuth } from "@/context/AuthContext";
import { api, errMsg, fmtDate } from "@/lib/api";
import { PageHeader } from "@/components/DataTable";
import { StatusBadge } from "@/components/Status";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OverviewTab } from "@/components/computer/OverviewTab";
import { SoftwareTab } from "@/components/computer/SoftwareTab";
import { HardwareTab } from "@/components/computer/HardwareTab";
import { NetworkTab } from "@/components/computer/NetworkTab";
import { UsersTab } from "@/components/computer/UsersTab";
import { HistoryTab } from "@/components/computer/HistoryTab";
import { ClientAssign } from "@/components/ClientAssign";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";

const TABS = [["overview", "Overview"], ["software", "Software"], ["hardware", "Hardware"], ["network", "Network"], ["users", "Users & Privileges"], ["history", "History"]];

export default function ComputerDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const [scanId, setScanId] = useState(null);
  const { data, error, reload } = useApi(`/computers/${id}`, scanId ? { scan_id: scanId } : {});
  if (error) return <div className="p-10 text-[var(--tt-red)] font-semibold" data-testid="computer-error">{error}</div>;
  if (!data) return <PageHeader eyebrow="Computer" title="Loading..." />;
  const { computer: c, scan } = data;
  const d = scan?.data || {};
  const isLatest = !scanId || scanId === c.last_scan_id;

  const editOwner = async () => {
    const owner = window.prompt("Owner / assigned user for this computer", c.owner || "");
    if (owner === null) return;
    try { await api.patch(`/computers/${id}`, { owner }); toast.success("Owner updated"); reload(); } catch (e) { toast.error(errMsg(e)); }
  };
  const remove = async () => {
    try { await api.delete(`/computers/${id}`); toast.success("Computer deleted"); nav("/computers"); } catch (e) { toast.error(errMsg(e)); }
  };

  return (
    <div>
      <PageHeader eyebrow={`${c.summary?.manufacturer || ""} ${c.summary?.model || ""}`} title={c.name} testid="computer-name">
        <Link to={`/computers/${id}/report${scanId ? `?scan_id=${scanId}` : ""}`} data-testid="view-report-btn"
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-[var(--tt-red)] text-white text-sm font-bold hover:bg-[#962810] transition-colors">
          <FileText size={16} /> Report & export
        </Link>
        {user?.role === "admin" && (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <button data-testid="delete-computer-btn" className="inline-flex items-center gap-2 px-3 py-2.5 rounded-md border border-[var(--tt-line)] text-sm font-semibold text-[var(--tt-muted)] hover:text-[var(--tt-red)] hover:border-[var(--tt-red)] transition-colors">
                <Trash2 size={15} /> Delete
              </button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete {c.name}?</AlertDialogTitle>
                <AlertDialogDescription>This permanently removes the computer and all {c.scan_count} of its scans.</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={remove} data-testid="confirm-delete-computer-btn" className="bg-[var(--tt-red)] hover:bg-[#962810]">Delete</AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        )}
      </PageHeader>
      <div className="px-10 pt-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        <StatusBadge status={c.status} testid="computer-status" />
        <span><span className="text-[var(--tt-muted)]">Serial </span><span className="mono">{c.serial || "-"}</span></span>
        <span className="flex items-center gap-1"><span className="text-[var(--tt-muted)]">Owner </span><span data-testid="computer-owner">{c.owner || "-"}</span>
          <button onClick={editOwner} data-testid="edit-owner-btn" className="text-[var(--tt-blue)] hover:text-[var(--tt-red)] transition-colors"><Pencil size={13} /></button></span>
        <ClientAssign key={`${c.client_id}-${c.site}`} computer={c} onDone={reload} />
        <span><span className="text-[var(--tt-muted)]">Weekly rescans </span><span data-testid="computer-scheduled">{c.scheduled ? `On${c.next_scheduled_run ? ` · next ${fmtDate(c.next_scheduled_run)}` : ""}` : "Off"}</span></span>
        <span><span className="text-[var(--tt-muted)]">Viewing scan </span>{fmtDate(scan?.scanned_at)}</span>
        {!isLatest && (
          <button onClick={() => setScanId(null)} data-testid="back-to-latest-btn" className="text-xs font-bold text-[var(--tt-red)] underline">Older scan shown - back to latest</button>
        )}
      </div>
      <div className="px-10 py-6">
        <Tabs defaultValue="overview">
          <TabsList className="bg-white border border-[var(--tt-line)] h-auto p-1 flex-wrap justify-start">
            {TABS.map(([v, l]) => (
              <TabsTrigger key={v} value={v} data-testid={`tab-${v}`}
                className="px-4 py-2 font-semibold data-[state=active]:bg-[var(--tt-blue)] data-[state=active]:text-white">{l}</TabsTrigger>
            ))}
          </TabsList>
          <div className="mt-6">
            <TabsContent value="overview"><OverviewTab d={d} flags={scan?.flags || []} /></TabsContent>
            <TabsContent value="software"><SoftwareTab d={d} /></TabsContent>
            <TabsContent value="hardware"><HardwareTab d={d} /></TabsContent>
            <TabsContent value="network"><NetworkTab d={d} /></TabsContent>
            <TabsContent value="users"><UsersTab d={d} /></TabsContent>
            <TabsContent value="history"><HistoryTab computerId={id} currentScanId={scan?.id} onView={setScanId} /></TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}
