import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import api from "../api/axios";
import { clearSession, getSession, isAllowedRole, setSession } from "../utils/auth";

export default function ProtectedRoute({ allowedRoles, children }) {
  const location = useLocation();
  const session = getSession();
  const accessToken = session?.access_token;
  const [verified, setVerified] = useState(false);
  const [invalidSession, setInvalidSession] = useState(false);

  useEffect(() => {
    let mounted = true;

    async function verifySession() {
      const currentSession = getSession();

      if (!currentSession?.access_token) {
        setVerified(true);
        return;
      }

      try {
        const response = await api.get("/auth/me");
        if (!mounted) return;
        setSession({
          ...currentSession,
          user: response.data.user,
        });
      } catch {
        if (!mounted) return;
        clearSession();
        setInvalidSession(true);
      } finally {
        if (mounted) setVerified(true);
      }
    }

    verifySession();

    return () => {
      mounted = false;
    };
  }, [accessToken]);

  if (!session?.access_token || invalidSession) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (!verified) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
        <div className="h-10 w-10 rounded-full border-2 border-gray-200 border-t-gray-950 animate-spin" />
      </div>
    );
  }

  if (!isAllowedRole(allowedRoles)) {
    const fallbackPath = session.user?.role === "super" ? "/super" : "/owner";
    return <Navigate to={fallbackPath} replace />;
  }

  return children;
}
