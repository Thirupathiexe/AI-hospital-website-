import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Navbar from "./components/Navbar";
import VoiceAssistant from "./components/VoiceAssistant";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import PatientDashboard from "./pages/PatientDashboard";
import StaffDashboard from "./pages/StaffDashboard";
import DoctorDashboard from "./pages/DoctorDashboard";
import { Spinner } from "./components/ui";

function Protected({ role, children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="grid min-h-[60vh] place-items-center"><Spinner /></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <Navigate to={`/${user.role}`} replace />;
  return children;
}

export default function App() {
  const { user } = useAuth();
  return (
    <div className="min-h-screen">
      <Navbar />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/patient" element={<Protected role="patient"><PatientDashboard /></Protected>} />
        <Route path="/staff" element={<Protected role="staff"><StaffDashboard /></Protected>} />
        <Route path="/doctor" element={<Protected role="doctor"><DoctorDashboard /></Protected>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      {user && user.role !== "doctor" && <VoiceAssistant />}
    </div>
  );
}
