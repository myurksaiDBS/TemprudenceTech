import { useState } from "react";
import { Trash2, UserPlus, Users } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, fmtDate } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

const EMPTY = { name: "", email: "", password: "" };

export const PortalUsersDialog = ({ client }) => {
  const [open, setOpen] = useState(false);
  const { data, reload } = useApi(open ? "/users" : null, { client_id: client.id });
  const [f, setF] = useState(EMPTY);
  const act = async (fn, msg) => { try { await fn(); toast.success(msg); reload(); return true; } catch (e) { toast.error(errMsg(e)); return false; } };
  const add = async (e) => {
    e.preventDefault();
    if (await act(() => api.post("/users", { ...f, role: "client", client_id: client.id }), "Portal user created")) setF(EMPTY);
  };
  const input = "w-full px-3 py-2 text-sm border border-[var(--tt-line)] rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--tt-blue)]/30";
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button data-testid={`portal-users-${client.name}`} className="inline-flex items-center gap-1 text-[var(--tt-blue)] hover:underline"><Users size={14} /> Portal users</button>
      </DialogTrigger>
      <DialogContent className="max-w-xl">
        <DialogHeader><DialogTitle className="text-[var(--tt-navy)]">Client portal: {client.name}</DialogTitle></DialogHeader>
        <p className="text-sm text-[var(--tt-muted)] -mt-2">Portal users sign in on the normal sign-in page and can only view and download this client's reports.</p>
        <ul className="divide-y divide-[var(--tt-line)] border-y border-[var(--tt-line)]" data-testid="portal-users-list">
          {(data || []).length === 0 && <li className="py-3 text-sm italic text-[var(--tt-muted)]">No portal users yet.</li>}
          {(data || []).map((u) => (
            <li key={u.id} className="py-2.5 flex items-center justify-between gap-3" data-testid={`portal-user-${u.email}`}>
              <div className="min-w-0">
                <div className="text-sm font-semibold">{u.name} {u.active === false && <span className="text-[10px] uppercase font-bold text-[var(--tt-red)] ml-1">Disabled</span>}</div>
                <div className="text-xs text-[var(--tt-muted)]">{u.email} · last sign-in {fmtDate(u.last_login)}</div>
              </div>
              <div className="flex gap-3 text-xs font-bold whitespace-nowrap">
                <button className="text-[var(--tt-blue)] hover:underline" data-testid={`portal-user-reset-${u.email}`}
                  onClick={() => { const pw = window.prompt(`New password for ${u.email} (min 8 characters)`); if (pw) act(() => api.patch(`/users/${u.id}`, { password: pw }), "Password updated"); }}>Reset password</button>
                <button className="text-[var(--tt-blue)] hover:underline" data-testid={`portal-user-toggle-${u.email}`}
                  onClick={() => act(() => api.patch(`/users/${u.id}`, { active: u.active === false }), "Status updated")}>{u.active === false ? "Enable" : "Disable"}</button>
                <button className="text-[var(--tt-red)] hover:underline inline-flex items-center gap-1" data-testid={`portal-user-delete-${u.email}`}
                  onClick={() => window.confirm(`Delete ${u.email}?`) && act(() => api.delete(`/users/${u.id}`), "Portal user deleted")}><Trash2 size={12} /> Delete</button>
              </div>
            </li>
          ))}
        </ul>
        <form onSubmit={add} className="grid grid-cols-2 gap-2" data-testid="portal-user-form">
          <input required placeholder="Full name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className={input} data-testid="portal-user-name-input" />
          <input required type="email" placeholder="Email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} className={input} data-testid="portal-user-email-input" />
          <input required type="password" minLength={8} placeholder="Temporary password (min 8)" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} className={`${input} col-span-2`} data-testid="portal-user-password-input" />
          <button type="submit" data-testid="portal-user-submit-btn" className="col-span-2 inline-flex justify-center items-center gap-2 py-2.5 rounded-md bg-[var(--tt-red)] text-white text-sm font-bold hover:bg-[#962810] transition-colors">
            <UserPlus size={16} /> Add portal user
          </button>
        </form>
      </DialogContent>
    </Dialog>
  );
};
