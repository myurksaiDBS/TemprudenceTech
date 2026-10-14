import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Computers from "@/pages/Computers";
import ComputerDetail from "@/pages/ComputerDetail";
import ComputerReport from "@/pages/ComputerReport";
import FleetReport from "@/pages/FleetReport";
import ScanPage from "@/pages/ScanPage";
import UsersAdmin from "@/pages/UsersAdmin";
import Clients from "@/pages/Clients";
import Alerts from "@/pages/Alerts";
import Settings from "@/pages/Settings";
import PortalLayout from "@/pages/portal/PortalLayout";
import PortalHome from "@/pages/portal/PortalHome";
import PortalReport from "@/pages/portal/PortalReport";

const Protected = ({ children, admin, portal = false }) => {
  const { user } = useAuth();
  if (user === null)
    return <div className="min-h-screen flex items-center justify-center text-[var(--tt-blue)]"><Loader2 className="animate-spin" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (portal !== (user.role === "client")) return <Navigate to={user.role === "client" ? "/portal" : "/"} replace />;
  if (admin && user.role !== "admin") return <Navigate to="/" replace />;
  return children;
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Protected portal><PortalLayout /></Protected>}>
            <Route path="/portal" element={<PortalHome />} />
            <Route path="/portal/summary" element={<PortalReport fleet />} />
            <Route path="/portal/computers/:id" element={<PortalReport />} />
          </Route>
          <Route element={<Protected portal={false}><Layout /></Protected>}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/computers" element={<Computers />} />
            <Route path="/computers/:id" element={<ComputerDetail />} />
            <Route path="/computers/:id/report" element={<ComputerReport />} />
            <Route path="/reports" element={<FleetReport />} />
            <Route path="/scan" element={<ScanPage />} />
            <Route path="/users" element={<Protected admin portal={false}><UsersAdmin /></Protected>} />
            <Route path="/settings" element={<Protected admin portal={false}><Settings /></Protected>} />
            <Route path="/clients" element={<Clients />} />
            <Route path="/alerts" element={<Alerts />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="bottom-right" richColors />
    </AuthProvider>
  );
}
