import { Navigate, useLocation } from "react-router-dom";
import { getSession, isAllowedRole } from "../utils/auth";

export default function ProtectedRoute({ allowedRoles, children }) {
  const location = useLocation();
  const session = getSession();

  if (!session?.access_token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (!isAllowedRole(allowedRoles)) {
    const fallbackPath = session.user?.role === "super" ? "/super" : "/owner";
    return <Navigate to={fallbackPath} replace />;
  }

  return children;
}
