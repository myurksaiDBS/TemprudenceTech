import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useApi } from "@/hooks/useApi";
import { useAuth } from "@/context/AuthContext";
import { api, errMsg, fmtDate } from "@/lib/api";
import { PageHeader, Section } from "@/components/DataTable";
import { BoolBadge } from "@/components/Status";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const Field = ({ label, ...p }) => (
  <label className="block mb-4">
    <span className="block text-xs font-semibold text-[var(--tt-muted)] mb-1">{label}</span>
    <input {...p} className="w-full px-3 py-2 text-sm border border-[var(--tt-line)] rounded-md focus:outline-none focus:ring-2 focus:ring-[var(--tt-blue)]/30" />
  </label>
);

const NewUser = ({ onDone }) => {
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ name: "", email: "", password: "", role: "technician" });
  const submit = async (e) => {
    e.preventDefault();
    try { await api.post("/users", f); toast.success("User created"); setOpen(false); setF({ name: "", email: "", password: "", role: "technician" }); onDone(); }
    catch (err) { toast.error(errMsg(err)); }
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button data-testid="add-user-btn" className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md bg-[var(--tt-red)] text-white text-sm font-bold hover:bg-[#962810] transition-colors"><Plus size={16} /> Add user</button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader><DialogTitle className="text-[var(--tt-navy)]">New user</DialogTitle></DialogHeader>
        <form onSubmit={submit} data-testid="new-user-form">
          <Field label="Full name" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="new-user-name-input" />
          <Field label="Email" type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="new-user-email-input" />
          <Field label="Temporary password (min 8 characters)" type="password" minLength={8} required value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} data-testid="new-user-password-input" />
          <span className="block text-xs font-semibold text-[var(--tt-muted)] mb-1">Role</span>
          <Select value={f.role} onValueChange={(role) => setF({ ...f, role })}>
            <SelectTrigger data-testid="new-user-role-select"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="technician">Technician</SelectItem><SelectItem value="admin">Admin</SelectItem></SelectContent>
          </Select>
          <button type="submit" data-testid="new-user-submit-btn" className="mt-6 w-full py-2.5 rounded-md bg-[var(--tt-blue)] text-white font-bold hover:bg-[var(--tt-navy)] transition-colors">Create user</button>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default function UsersAdmin() {
  const { user: me } = useAuth();
  const { data, reload } = useApi("/users");
  const act = async (fn, msg) => { try { await fn(); toast.success(msg); reload(); } catch (e) { toast.error(errMsg(e)); } };
  const resetPw = (u) => {
    const pw = window.prompt(`New password for ${u.email} (min 8 characters)`);
    if (pw) act(() => api.patch(`/users/${u.id}`, { password: pw }), "Password updated");
  };
  return (
    <div>
      <PageHeader eyebrow="Administration" title="Users" testid="users-title"><NewUser onDone={reload} /></PageHeader>
      <div className="px-10 py-8">
        <Section title="Console accounts">
          <div className="tt-card overflow-auto">
            <table className="tt-table w-full border-collapse" data-testid="users-table">
              <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Last sign-in</th><th>Actions</th></tr></thead>
              <tbody>
                {(data || []).map((u) => (
                  <tr key={u.id} data-testid={`user-row-${u.email}`}>
                    <td className="font-semibold">{u.name}</td>
                    <td>{u.email}</td>
                    <td>
                      <select value={u.role} disabled={u.id === me.id} data-testid={`user-role-${u.email}`}
                        onChange={(e) => act(() => api.patch(`/users/${u.id}`, { role: e.target.value }), "Role updated")}
                        className="border border-[var(--tt-line)] rounded px-2 py-1 text-sm bg-white">
                        <option value="technician">Technician</option><option value="admin">Admin</option>
                      </select>
                    </td>
                    <td><BoolBadge value={u.active !== false} yes="Active" no="Disabled" /></td>
                    <td>{fmtDate(u.last_login)}</td>
                    <td className="whitespace-nowrap space-x-3">
                      <button onClick={() => resetPw(u)} className="text-xs font-bold text-[var(--tt-blue)] hover:underline" data-testid={`reset-pw-${u.email}`}>Reset password</button>
                      {u.id !== me.id && (
                        <>
                          <button onClick={() => act(() => api.patch(`/users/${u.id}`, { active: u.active === false }), "Status updated")} className="text-xs font-bold text-[var(--tt-blue)] hover:underline" data-testid={`toggle-user-${u.email}`}>
                            {u.active === false ? "Enable" : "Disable"}
                          </button>
                          <button onClick={() => window.confirm(`Delete ${u.email}?`) && act(() => api.delete(`/users/${u.id}`), "User deleted")} className="text-xs font-bold text-[var(--tt-red)] hover:underline inline-flex items-center gap-1" data-testid={`delete-user-${u.email}`}>
                            <Trash2 size={12} /> Delete
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      </div>
    </div>
  );
}
