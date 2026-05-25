import { useNavigate } from "react-router-dom";
import { clearSession, getUser } from "../utils/auth";

export default function DashboardHeader({ eyebrow, title, subtitle, action }) {
  const navigate = useNavigate();
  const user = getUser();

  function logout() {
    clearSession();
    navigate("/login", { replace: true });
  }

  return (
    <header className="sticky top-0 z-10 border-b border-gray-100 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          {typeof eyebrow === "string" && (
            <p className="text-xs font-semibold uppercase tracking-normal text-orange-700">
              {eyebrow}
            </p>
          )}
          {eyebrow && typeof eyebrow !== "string" && eyebrow}
          <h1 className="text-2xl font-bold text-gray-950">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
          {user?.email && <p className="mt-1 text-xs text-gray-400">{user.email}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          {action}
          <button
            type="button"
            onClick={logout}
            className="inline-flex h-10 items-center justify-center rounded-lg border border-gray-200 bg-white px-4 text-sm font-semibold text-gray-900 hover:bg-gray-50"
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
