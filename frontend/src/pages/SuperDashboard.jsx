import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../api/axios";
import DashboardHeader from "../components/DashboardHeader";

function buildSlug(value) {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export default function SuperDashboard() {
  const [restaurants, setRestaurants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [ownerForm, setOwnerForm] = useState({
    email: "",
    password: "",
    full_name: "",
  });
  const [createdOwner, setCreatedOwner] = useState(null);
  const [formData, setFormData] = useState({
    owner_id: "",
    name: "",
    slug: "",
    city: "",
  });

  useEffect(() => {
    let mounted = true;

    async function fetchRestaurants() {
      try {
        const response = await api.get("/super/restaurants");
        if (mounted) setRestaurants(response.data || []);
      } catch (error) {
        console.error("Failed to load restaurants:", error);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    fetchRestaurants();
    return () => {
      mounted = false;
    };
  }, []);

  async function createRestaurant(e) {
    e.preventDefault();
    setSubmitting(true);
    setSuccessMessage("");

    try {
      await api.post("/super/restaurants", {
        ...formData,
        logo_url: null,
        is_active: true,
      });

      const response = await api.get("/super/restaurants");
      setRestaurants(response.data || []);

      setFormData({
        owner_id: "",
        name: "",
        slug: "",
        city: "",
      });
      setShowForm(false);
      setSuccessMessage("Restaurant created successfully!");
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (error) {
      console.error("Failed to create restaurant:", error);
      alert(error?.response?.data?.detail || "Failed to create restaurant");
    } finally {
      setSubmitting(false);
    }
  }

  async function createOwner(e) {
    e.preventDefault();
    setSubmitting(true);
    setSuccessMessage("");

    try {
      const response = await api.post("/super/owners", {
        email: ownerForm.email,
        password: ownerForm.password,
        full_name: ownerForm.full_name || null,
      });
      setCreatedOwner(response.data);
      setFormData((current) => ({
        ...current,
        owner_id: response.data.id,
      }));
      setOwnerForm({
        email: "",
        password: "",
        full_name: "",
      });
      setSuccessMessage("Owner account created. Owner UUID filled into restaurant form.");
      setTimeout(() => setSuccessMessage(""), 3000);
    } catch (error) {
      console.error("Failed to create owner:", error);
      alert(error?.response?.data?.detail || "Failed to create owner account");
    } finally {
      setSubmitting(false);
    }
  }

  function handleChange(e) {
    const nextFormData = {
      ...formData,
      [e.target.name]: e.target.value,
    };

    if (e.target.name === "name" && !formData.slug) {
      nextFormData.slug = buildSlug(e.target.value);
    }

    setFormData({
      ...nextFormData,
    });
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="mx-auto max-w-6xl">
          <div className="mb-6 h-8 w-1/3 rounded bg-gray-200 animate-pulse" />
          <div className="mb-6 grid gap-3 sm:grid-cols-3">
            {[1, 2, 3].map((s) => (
              <div key={s} className="h-24 rounded-lg bg-white p-4 animate-pulse" />
            ))}
          </div>
          <div className="h-80 rounded-lg bg-white animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <DashboardHeader
        eyebrow="Platform admin"
        title="Restaurants"
        subtitle="Create restaurants, owner accounts, and operational menu tools."
        action={
          <button
            onClick={() => setShowForm((current) => !current)}
            className="inline-flex h-10 items-center justify-center rounded-lg bg-black px-4 text-sm font-semibold text-white hover:bg-gray-900"
          >
            {showForm ? "Close form" : "Create restaurant"}
          </button>
        }
      />

      <main className="mx-auto max-w-6xl px-4 py-6">
        {successMessage && (
          <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-800">
            {successMessage}
          </div>
        )}

        <section className="mb-6 grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-gray-100 bg-white p-4">
            <p className="text-sm font-medium text-gray-500">Total restaurants</p>
            <p className="mt-2 text-2xl font-bold text-gray-950">{restaurants.length}</p>
          </div>
          <div className="rounded-lg border border-gray-100 bg-white p-4">
            <p className="text-sm font-medium text-gray-500">Active</p>
            <p className="mt-2 text-2xl font-bold text-gray-950">
              {restaurants.filter((restaurant) => restaurant.is_active).length}
            </p>
          </div>
          <div className="rounded-lg border border-gray-100 bg-white p-4">
            <p className="text-sm font-medium text-gray-500">Inactive</p>
            <p className="mt-2 text-2xl font-bold text-gray-950">
              {restaurants.filter((restaurant) => !restaurant.is_active).length}
            </p>
          </div>
        </section>

        {showForm && (
          <section className="mb-6 grid gap-4 lg:grid-cols-[360px_1fr]">
            <form onSubmit={createOwner} className="rounded-lg border border-gray-100 bg-white p-4">
              <h2 className="text-base font-bold text-gray-950">Create owner account</h2>
              <p className="mt-1 text-sm text-gray-500">Creates a Supabase Auth user with owner role metadata.</p>
              <div className="mt-4 space-y-3">
                <input
                  type="email"
                  value={ownerForm.email}
                  onChange={(event) => setOwnerForm((current) => ({ ...current, email: event.target.value }))}
                  required
                  className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                  placeholder="owner@example.com"
                />
                <input
                  type="text"
                  value={ownerForm.full_name}
                  onChange={(event) => setOwnerForm((current) => ({ ...current, full_name: event.target.value }))}
                  className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                  placeholder="Owner name"
                />
                <input
                  type="password"
                  value={ownerForm.password}
                  onChange={(event) => setOwnerForm((current) => ({ ...current, password: event.target.value }))}
                  required
                  minLength="6"
                  className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                  placeholder="Temporary password"
                />
              </div>
              <button
                type="submit"
                disabled={submitting}
                className="mt-4 h-10 w-full rounded-lg border border-gray-200 bg-white px-4 text-sm font-semibold text-gray-900 hover:bg-gray-50 disabled:opacity-50"
              >
                Create owner
              </button>
              {createdOwner && (
                <p className="mt-3 break-all rounded bg-gray-50 p-3 text-xs text-gray-600">
                  Owner UUID: {createdOwner.id}
                </p>
              )}
            </form>

            <form
              onSubmit={createRestaurant}
              className="grid gap-4 rounded-lg border border-gray-100 bg-white p-4 sm:grid-cols-2"
            >
              <div className="sm:col-span-2">
                <h2 className="text-base font-bold text-gray-950">Create restaurant</h2>
                <p className="mt-1 text-sm text-gray-500">Owner UUID must come from the authenticated owner account.</p>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Owner UUID</label>
                <input
                  type="text"
                  name="owner_id"
                  placeholder="Enter owner UUID"
                  value={formData.owner_id}
                  onChange={handleChange}
                  required
                  className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Restaurant name</label>
                <input
                  type="text"
                  name="name"
                  placeholder="Enter restaurant name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Public slug</label>
                <input
                  type="text"
                  name="slug"
                  placeholder="e.g., pizza-cafe"
                  value={formData.slug}
                  onChange={handleChange}
                  required
                  className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                />
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">City</label>
                <input
                  type="text"
                  name="city"
                  placeholder="Enter city"
                  value={formData.city}
                  onChange={handleChange}
                  required
                  className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                />
              </div>

              <div className="flex gap-3 sm:col-span-2">
                <button
                  type="submit"
                  disabled={submitting}
                  className="h-10 flex-1 rounded-lg bg-black px-4 text-sm font-semibold text-white hover:bg-gray-900 disabled:opacity-50"
                >
                  {submitting ? "Creating..." : "Create Restaurant"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="h-10 flex-1 rounded-lg border border-gray-200 bg-white px-4 text-sm font-semibold text-gray-900 hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </form>
          </section>
        )}

        <section className="rounded-lg border border-gray-100 bg-white">
          <div className="border-b border-gray-100 px-4 py-4">
            <h2 className="text-base font-bold text-gray-950">Restaurant management</h2>
            <p className="mt-1 text-sm text-gray-500">Open a restaurant to manage menu categories and items.</p>
          </div>

          {restaurants.length === 0 ? (
            <div className="p-8 text-center">
              <p className="font-semibold text-gray-950">No restaurants yet</p>
              <p className="mt-1 text-sm text-gray-500">Create the first restaurant to start onboarding menus.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {restaurants.map((restaurant) => (
                <Link
                  to={`/super/restaurants/${restaurant.id}`}
                  key={restaurant.id}
                  className="block p-4 hover:bg-gray-50"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate font-semibold text-gray-950">
                        {restaurant.name}
                      </h3>
                      <div className="mt-2 flex flex-wrap gap-2 text-sm text-gray-600">
                        <span>{restaurant.city}</span>
                        <span className="font-mono text-xs text-gray-500">{restaurant.slug}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span
                        className={`rounded px-2 py-1 text-xs font-semibold ${
                          restaurant.is_active
                            ? "bg-green-50 text-green-700"
                            : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {restaurant.is_active ? "Active" : "Inactive"}
                      </span>
                      <span className="text-sm font-semibold text-gray-900">Open</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
