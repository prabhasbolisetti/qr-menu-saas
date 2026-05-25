import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import api from "../api/axios";
import { setSession } from "../utils/auth";

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      const response = await api.post("/auth/login", formData);
      setSession(response.data);

      const role = response.data.user.role;
      const requestedPath = location.state?.from;
      const fallbackPath = role === "super" ? "/super" : "/owner";

      navigate(requestedPath || fallbackPath, { replace: true });
    } catch (err) {
      console.error("Login failed:", err);
      setError(err?.response?.data?.detail || "Unable to login");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <main className="w-full max-w-sm rounded-lg border border-gray-100 bg-white p-6 shadow-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-normal text-orange-700">QR Menu SaaS</p>
          <h1 className="mt-2 text-2xl font-bold text-gray-950">Login</h1>
          <p className="mt-1 text-sm text-gray-500">Access your restaurant or platform dashboard.</p>
        </div>

        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(event) =>
                setFormData((current) => ({ ...current, email: event.target.value }))
              }
              required
              className="h-11 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
              placeholder="owner@example.com"
            />
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Password</label>
            <input
              type="password"
              value={formData.password}
              onChange={(event) =>
                setFormData((current) => ({ ...current, password: event.target.value }))
              }
              required
              className="h-11 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
              placeholder="Password"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="h-11 w-full rounded-lg bg-black px-4 text-sm font-semibold text-white hover:bg-gray-900 disabled:opacity-50"
          >
            {submitting ? "Logging in..." : "Login"}
          </button>
        </form>
      </main>
    </div>
  );
}
