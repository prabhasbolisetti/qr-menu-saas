import { useEffect, useMemo, useState } from "react";
import api from "../api/axios";
import DashboardHeader from "../components/DashboardHeader";

const emptyCategoryForm = {
  name: "",
  icon_emoji: "",
  display_order: 0,
};

const emptyItemForm = {
  category_id: "",
  name: "",
  description: "",
  price: "",
  mrp_price: "",
  image_url: "",
  is_available: true,
  is_veg: true,
  is_special: false,
  display_order: 0,
};

function formatPrice(amount) {
  if (amount == null || amount === "") return "Not set";

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

function groupItemsByCategory(categories, items) {
  return categories.map((category) => ({
    ...category,
    items: items.filter((item) => item.category_id === category.id),
  }));
}

export default function OwnerDashboard() {
  const [restaurant, setRestaurant] = useState(null);
  const [categories, setCategories] = useState([]);
  const [items, setItems] = useState([]);
  const [qr, setQr] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [submitting, setSubmitting] = useState("");
  const [categoryForm, setCategoryForm] = useState(emptyCategoryForm);
  const [itemForm, setItemForm] = useState(emptyItemForm);
  const [imageFile, setImageFile] = useState(null);
  const [editingItemId, setEditingItemId] = useState("");
  const [editDrafts, setEditDrafts] = useState({});

  async function loadDashboard() {
    setError("");

    try {
      const [restaurantResponse, categoriesResponse, itemsResponse, qrResponse] = await Promise.all([
        api.get("/owner/restaurant"),
        api.get("/owner/categories"),
        api.get("/owner/items"),
        api.get("/owner/restaurant/qr"),
      ]);

      const nextItems = itemsResponse.data || [];
      setRestaurant(restaurantResponse.data);
      setCategories(categoriesResponse.data || []);
      setItems(nextItems);
      setQr(qrResponse.data);
      setEditDrafts(
        nextItems.reduce((drafts, item) => {
          drafts[item.id] = {
            name: item.name || "",
            description: item.description || "",
            price: item.price ?? "",
            mrp_price: item.mrp_price ?? "",
            image_url: item.image_url || "",
            is_available: Boolean(item.is_available),
            is_veg: Boolean(item.is_veg),
            is_special: Boolean(item.is_special),
          };
          return drafts;
        }, {})
      );
    } catch (err) {
      console.error("Failed to load owner dashboard:", err);
      setError(err?.response?.data?.detail || "Unable to load owner dashboard");
    }
  }

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      await loadDashboard();
      if (mounted) setLoading(false);
    }

    load();
    return () => {
      mounted = false;
    };
  }, []);

  const menu = useMemo(() => groupItemsByCategory(categories, items), [categories, items]);

  const metrics = useMemo(() => {
    const availableItems = items.filter((item) => item.is_available).length;

    return {
      totalItems: items.length,
      availableItems,
      unavailableItems: items.length - availableItems,
      categories: categories.length,
    };
  }, [categories.length, items]);

  function showSuccess(message) {
    setSuccessMessage(message);
    setTimeout(() => setSuccessMessage(""), 3000);
  }

  async function createCategory(event) {
    event.preventDefault();
    setSubmitting("category");
    setError("");

    try {
      await api.post("/owner/categories", {
        name: categoryForm.name,
        icon_emoji: categoryForm.icon_emoji || null,
        display_order: Number(categoryForm.display_order) || 0,
      });
      setCategoryForm(emptyCategoryForm);
      await loadDashboard();
      showSuccess("Category created");
    } catch (err) {
      console.error("Failed to create category:", err);
      setError(err?.response?.data?.detail || "Unable to create category");
    } finally {
      setSubmitting("");
    }
  }

  async function uploadImageIfNeeded() {
    if (!imageFile) return itemForm.image_url || null;

    const data = new FormData();
    data.append("file", imageFile);

    const response = await api.post("/owner/upload/image", data, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    return response.data.image_url;
  }

  async function createItem(event) {
    event.preventDefault();
    setSubmitting("item");
    setError("");

    try {
      const imageUrl = await uploadImageIfNeeded();
      await api.post("/owner/items", {
        category_id: itemForm.category_id,
        name: itemForm.name,
        description: itemForm.description || null,
        price: Number(itemForm.price),
        mrp_price: itemForm.mrp_price === "" ? null : Number(itemForm.mrp_price),
        image_url: imageUrl,
        is_available: itemForm.is_available,
        is_veg: itemForm.is_veg,
        is_special: itemForm.is_special,
        display_order: Number(itemForm.display_order) || 0,
      });

      setItemForm({ ...emptyItemForm, category_id: itemForm.category_id });
      setImageFile(null);
      await loadDashboard();
      showSuccess("Item created");
    } catch (err) {
      console.error("Failed to create item:", err);
      setError(err?.response?.data?.detail || "Unable to create item");
    } finally {
      setSubmitting("");
    }
  }

  async function updateItem(itemId) {
    const draft = editDrafts[itemId];
    setSubmitting(itemId);
    setError("");

    try {
      await api.put(`/owner/items/${itemId}`, {
        name: draft.name,
        description: draft.description || null,
        price: draft.price === "" ? null : Number(draft.price),
        mrp_price: draft.mrp_price === "" ? null : Number(draft.mrp_price),
        image_url: draft.image_url || null,
        is_available: draft.is_available,
        is_veg: draft.is_veg,
        is_special: draft.is_special,
      });
      setEditingItemId("");
      await loadDashboard();
      showSuccess("Item updated");
    } catch (err) {
      console.error("Failed to update item:", err);
      setError(err?.response?.data?.detail || "Unable to update item");
    } finally {
      setSubmitting("");
    }
  }

  async function toggleAvailability(item) {
    setSubmitting(item.id);
    setError("");

    try {
      await api.patch(`/owner/items/${item.id}/toggle`);
      await loadDashboard();
      showSuccess(item.is_available ? "Item hidden" : "Item available");
    } catch (err) {
      console.error("Failed to toggle item:", err);
      setError(err?.response?.data?.detail || "Unable to update availability");
    } finally {
      setSubmitting("");
    }
  }

  async function deleteItem(itemId) {
    if (!window.confirm("Delete this menu item?")) return;

    setSubmitting(itemId);
    setError("");

    try {
      await api.delete(`/owner/items/${itemId}`);
      await loadDashboard();
      showSuccess("Item deleted");
    } catch (err) {
      console.error("Failed to delete item:", err);
      setError(err?.response?.data?.detail || "Unable to delete item");
    } finally {
      setSubmitting("");
    }
  }

  async function deleteCategory(categoryId) {
    if (!window.confirm("Delete this category? Items in this category may also be affected.")) return;

    setSubmitting(categoryId);
    setError("");

    try {
      await api.delete(`/owner/categories/${categoryId}`);
      await loadDashboard();
      showSuccess("Category deleted");
    } catch (err) {
      console.error("Failed to delete category:", err);
      setError(err?.response?.data?.detail || "Unable to delete category");
    } finally {
      setSubmitting("");
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="mx-auto max-w-6xl space-y-4">
          <div className="h-24 rounded-lg border border-gray-100 bg-white animate-pulse" />
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((item) => (
              <div key={item} className="h-24 rounded-lg border border-gray-100 bg-white animate-pulse" />
            ))}
          </div>
          <div className="h-80 rounded-lg border border-gray-100 bg-white animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <DashboardHeader
        eyebrow="Owner"
        title={restaurant?.name || "Owner dashboard"}
        subtitle={restaurant?.city || "Manage your restaurant menu"}
        action={
          restaurant?.slug && (
            <a
              href={`/menu/${restaurant.slug}`}
              className="inline-flex h-10 items-center justify-center rounded-lg bg-black px-4 text-sm font-semibold text-white hover:bg-gray-900"
            >
              View public menu
            </a>
          )
        }
      />

      <main className="mx-auto max-w-6xl px-4 py-6">
        {successMessage && (
          <div className="mb-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-800">
            {successMessage}
          </div>
        )}
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
            {error}
          </div>
        )}

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-gray-100 bg-white p-4">
            <p className="text-sm font-medium text-gray-500">Total items</p>
            <p className="mt-2 text-2xl font-bold text-gray-950">{metrics.totalItems}</p>
          </div>
          <div className="rounded-lg border border-gray-100 bg-white p-4">
            <p className="text-sm font-medium text-gray-500">Available</p>
            <p className="mt-2 text-2xl font-bold text-gray-950">{metrics.availableItems}</p>
          </div>
          <div className="rounded-lg border border-gray-100 bg-white p-4">
            <p className="text-sm font-medium text-gray-500">Hidden</p>
            <p className="mt-2 text-2xl font-bold text-gray-950">{metrics.unavailableItems}</p>
          </div>
          <div className="rounded-lg border border-gray-100 bg-white p-4">
            <p className="text-sm font-medium text-gray-500">Categories</p>
            <p className="mt-2 text-2xl font-bold text-gray-950">{metrics.categories}</p>
          </div>
        </section>

        {qr && (
          <section className="mt-6 rounded-lg border border-gray-100 bg-white p-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              <img src={qr.qr_image_url} alt="Restaurant QR code" className="h-32 w-32 rounded border border-gray-100" />
              <div className="min-w-0 flex-1">
                <h2 className="font-bold text-gray-950">Restaurant QR code</h2>
                <p className="mt-1 break-all text-sm text-gray-500">{qr.menu_url}</p>
              </div>
            </div>
          </section>
        )}

        <div className="mt-6 grid gap-6 lg:grid-cols-[360px_1fr]">
          <aside className="space-y-4">
            <form onSubmit={createCategory} className="rounded-lg border border-gray-100 bg-white p-4">
              <h2 className="text-base font-bold text-gray-950">Add category</h2>
              <div className="mt-4 grid gap-3">
                <input
                  value={categoryForm.name}
                  onChange={(event) => setCategoryForm((current) => ({ ...current, name: event.target.value }))}
                  required
                  className="h-10 rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                  placeholder="Category name"
                />
                <div className="grid grid-cols-2 gap-3">
                  <input
                    value={categoryForm.icon_emoji}
                    onChange={(event) => setCategoryForm((current) => ({ ...current, icon_emoji: event.target.value }))}
                    className="h-10 rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                    placeholder="Icon"
                  />
                  <input
                    type="number"
                    value={categoryForm.display_order}
                    onChange={(event) => setCategoryForm((current) => ({ ...current, display_order: event.target.value }))}
                    className="h-10 rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                    placeholder="Order"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={submitting === "category"}
                className="mt-4 h-10 w-full rounded-lg bg-black px-4 text-sm font-semibold text-white hover:bg-gray-900 disabled:opacity-50"
              >
                Create category
              </button>
            </form>

            <form onSubmit={createItem} className="rounded-lg border border-gray-100 bg-white p-4">
              <h2 className="text-base font-bold text-gray-950">Add item</h2>
              <div className="mt-4 space-y-3">
                <select
                  value={itemForm.category_id}
                  onChange={(event) => setItemForm((current) => ({ ...current, category_id: event.target.value }))}
                  required
                  className="h-10 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm outline-none focus:border-gray-400"
                >
                  <option value="">Select category</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>{category.name}</option>
                  ))}
                </select>
                <input
                  value={itemForm.name}
                  onChange={(event) => setItemForm((current) => ({ ...current, name: event.target.value }))}
                  required
                  className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                  placeholder="Item name"
                />
                <textarea
                  value={itemForm.description}
                  onChange={(event) => setItemForm((current) => ({ ...current, description: event.target.value }))}
                  rows="3"
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-gray-400"
                  placeholder="Description"
                />
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="number"
                    min="0"
                    value={itemForm.price}
                    onChange={(event) => setItemForm((current) => ({ ...current, price: event.target.value }))}
                    required
                    className="h-10 rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                    placeholder="Price"
                  />
                  <input
                    type="number"
                    min="0"
                    value={itemForm.mrp_price}
                    onChange={(event) => setItemForm((current) => ({ ...current, mrp_price: event.target.value }))}
                    className="h-10 rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                    placeholder="MRP"
                  />
                </div>
                <input
                  type="url"
                  value={itemForm.image_url}
                  onChange={(event) => setItemForm((current) => ({ ...current, image_url: event.target.value }))}
                  className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                  placeholder="Image URL"
                />
                <input
                  type="file"
                  accept="image/*"
                  onChange={(event) => setImageFile(event.target.files?.[0] || null)}
                  className="block w-full text-sm text-gray-600 file:mr-3 file:h-9 file:rounded-lg file:border-0 file:bg-gray-100 file:px-3 file:text-sm file:font-semibold file:text-gray-900"
                />
                <div className="grid grid-cols-2 gap-2">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <input type="checkbox" checked={itemForm.is_veg} onChange={(event) => setItemForm((current) => ({ ...current, is_veg: event.target.checked }))} />
                    Veg
                  </label>
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <input type="checkbox" checked={itemForm.is_special} onChange={(event) => setItemForm((current) => ({ ...current, is_special: event.target.checked }))} />
                    Bestseller
                  </label>
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <input type="checkbox" checked={itemForm.is_available} onChange={(event) => setItemForm((current) => ({ ...current, is_available: event.target.checked }))} />
                    Available
                  </label>
                  <input
                    type="number"
                    value={itemForm.display_order}
                    onChange={(event) => setItemForm((current) => ({ ...current, display_order: event.target.value }))}
                    className="h-10 rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                    placeholder="Order"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={submitting === "item" || categories.length === 0}
                className="mt-4 h-10 w-full rounded-lg bg-black px-4 text-sm font-semibold text-white hover:bg-gray-900 disabled:opacity-50"
              >
                Create item
              </button>
            </form>
          </aside>

          <section className="space-y-4">
            {menu.length === 0 ? (
              <div className="rounded-lg border border-gray-100 bg-white p-8 text-center">
                <p className="font-semibold text-gray-950">No categories yet</p>
                <p className="mt-1 text-sm text-gray-500">Create a category to start building the menu.</p>
              </div>
            ) : (
              menu.map((category) => (
                <div key={category.id} className="rounded-lg border border-gray-100 bg-white">
                  <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
                    <div>
                      <h2 className="font-bold text-gray-950">{category.name}</h2>
                      <p className="text-sm text-gray-500">{category.items.length} items</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => deleteCategory(category.id)}
                      className="rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50"
                    >
                      Delete category
                    </button>
                  </div>

                  <div className="divide-y divide-gray-100">
                    {category.items.length === 0 ? (
                      <div className="p-4 text-sm text-gray-500">No items in this category.</div>
                    ) : (
                      category.items.map((item) => {
                        const draft = editDrafts[item.id] || {};
                        const isEditing = editingItemId === item.id;

                        return (
                          <div key={item.id} className="p-4">
                            {isEditing ? (
                              <div className="grid gap-3">
                                <input
                                  value={draft.name || ""}
                                  onChange={(event) => setEditDrafts((current) => ({ ...current, [item.id]: { ...draft, name: event.target.value } }))}
                                  className="h-10 rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                                />
                                <textarea
                                  value={draft.description || ""}
                                  onChange={(event) => setEditDrafts((current) => ({ ...current, [item.id]: { ...draft, description: event.target.value } }))}
                                  rows="2"
                                  className="rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-gray-400"
                                />
                                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                                  <input type="number" value={draft.price ?? ""} onChange={(event) => setEditDrafts((current) => ({ ...current, [item.id]: { ...draft, price: event.target.value } }))} className="h-10 rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400" />
                                  <input type="number" value={draft.mrp_price ?? ""} onChange={(event) => setEditDrafts((current) => ({ ...current, [item.id]: { ...draft, mrp_price: event.target.value } }))} className="h-10 rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400" />
                                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                                    <input type="checkbox" checked={Boolean(draft.is_veg)} onChange={(event) => setEditDrafts((current) => ({ ...current, [item.id]: { ...draft, is_veg: event.target.checked } }))} />
                                    Veg
                                  </label>
                                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                                    <input type="checkbox" checked={Boolean(draft.is_special)} onChange={(event) => setEditDrafts((current) => ({ ...current, [item.id]: { ...draft, is_special: event.target.checked } }))} />
                                    Bestseller
                                  </label>
                                </div>
                                <div className="flex gap-2">
                                  <button type="button" onClick={() => updateItem(item.id)} disabled={submitting === item.id} className="h-9 rounded-lg bg-black px-3 text-xs font-semibold text-white hover:bg-gray-900 disabled:opacity-50">Save</button>
                                  <button type="button" onClick={() => setEditingItemId("")} className="h-9 rounded-lg border border-gray-200 px-3 text-xs font-semibold text-gray-900 hover:bg-gray-50">Cancel</button>
                                </div>
                              </div>
                            ) : (
                              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <div className="min-w-0">
                                  <p className="font-semibold text-gray-950">{item.name}</p>
                                  <p className="mt-1 text-sm text-gray-500">
                                    {formatPrice(item.price)} / {item.is_available ? "Available" : "Hidden"} / {item.is_veg ? "Veg" : "Non-veg"}
                                  </p>
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  <button type="button" onClick={() => toggleAvailability(item)} className="h-9 rounded-lg border border-gray-200 px-3 text-xs font-semibold text-gray-900 hover:bg-gray-50">
                                    {item.is_available ? "Hide" : "Show"}
                                  </button>
                                  <button type="button" onClick={() => setEditingItemId(item.id)} className="h-9 rounded-lg border border-gray-200 px-3 text-xs font-semibold text-gray-900 hover:bg-gray-50">Edit</button>
                                  <button type="button" onClick={() => deleteItem(item.id)} className="h-9 rounded-lg border border-red-200 px-3 text-xs font-semibold text-red-700 hover:bg-red-50">Delete</button>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              ))
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
