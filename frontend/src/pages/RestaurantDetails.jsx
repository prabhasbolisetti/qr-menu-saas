import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../api/axios";
import DashboardHeader from "../components/DashboardHeader";
import CategorySection from "../components/CategorySection";
import { downloadImage } from "../utils/download";

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
  is_bestseller: false,
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

function buildEditDrafts(menu) {
  return menu.reduce((drafts, category) => {
    category.items.forEach((item) => {
      drafts[item.id] = {
        name: item.name || "",
        price: item.price ?? "",
        mrp_price: item.mrp_price ?? "",
        description: item.description || "",
        image_url: item.image_url || "",
        is_available: Boolean(item.is_available),
        is_veg: Boolean(item.is_veg),
        is_special: Boolean(item.is_special),
        is_bestseller: Boolean(item.is_bestseller),
      };
    });
    return drafts;
  }, {});
}

function groupItemsByCategory(categories, items) {
  return categories.map((category) => ({
    ...category,
    items: items.filter((item) => item.category_id === category.id),
  }));
}

export default function RestaurantDetails() {
  const { id } = useParams();
  const [restaurant, setRestaurant] = useState(null);
  const [categories, setCategories] = useState([]);
  const [menu, setMenu] = useState([]);
  const [items, setItems] = useState([]);
  const [qr, setQr] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [categoryForm, setCategoryForm] = useState(emptyCategoryForm);
  const [itemForm, setItemForm] = useState(emptyItemForm);
  const [imageFile, setImageFile] = useState(null);
  const [submitting, setSubmitting] = useState("");
  const [editingItemId, setEditingItemId] = useState("");
  const [editDrafts, setEditDrafts] = useState({});

  const loadRestaurant = useCallback(async () => {
    setError("");

    try {
      const restaurantResponse = await api.get(`/super/restaurants/${id}`);
      const foundRestaurant = restaurantResponse.data;
      const [categoriesResponse, itemsResponse] = await Promise.all([
        api.get(`/super/restaurants/${id}/categories`),
        api.get(`/super/restaurants/${id}/items`),
      ]);
      const nextCategories = categoriesResponse.data || [];
      const nextItems = itemsResponse.data || [];
      const nextMenu = groupItemsByCategory(nextCategories, nextItems);

      setRestaurant(foundRestaurant);
      setQr(foundRestaurant?.qr || null);
      setCategories(nextCategories);
      setItems(nextItems);
      setMenu(nextMenu);
      setEditDrafts(buildEditDrafts(nextMenu));
    } catch (err) {
      console.error("Failed to load restaurant:", err);
      setError(err?.response?.data?.detail || "Failed to load restaurant details");
    }
  }, [id]);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      await loadRestaurant();
      if (mounted) setLoading(false);
    }

    load();
    return () => {
      mounted = false;
    };
  }, [loadRestaurant]);

  const metrics = useMemo(() => {
    const specialCount = items.filter((item) => item.is_special).length;
    const bestsellerCount = items.filter((item) => item.is_bestseller).length;

    return {
      categories: categories.length,
      items: items.length,
      specials: specialCount,
      bestsellers: bestsellerCount,
    };
  }, [categories.length, items]);

  const managementMenu = useMemo(
    () =>
      categories.map((category) => {
        const visibleCategory = menu.find((current) => current.id === category.id);

        return {
          ...category,
          items: visibleCategory?.items || [],
        };
      }),
    [categories, menu]
  );

  function showSuccess(message) {
    setSuccessMessage(message);
    setTimeout(() => setSuccessMessage(""), 3000);
  }

  async function createCategory(event) {
    event.preventDefault();
    setSubmitting("category");
    setError("");

    try {
      const response = await api.post("/super/categories", {
        restaurant_id: restaurant.id,
        name: categoryForm.name,
        icon_emoji: categoryForm.icon_emoji || null,
        display_order: Number(categoryForm.display_order) || 0,
      });

      setCategories((currentCategories) => [...currentCategories, response.data]);
      setItemForm((current) => ({
        ...current,
        category_id: current.category_id || response.data.id,
      }));
      setCategoryForm(emptyCategoryForm);
      showSuccess("Category created");
    } catch (err) {
      console.error("Failed to create category:", err);
      setError(err?.response?.data?.detail || "Failed to create category");
    } finally {
      setSubmitting("");
    }
  }

  async function uploadImageIfNeeded() {
    if (!imageFile) return itemForm.image_url || null;

    const data = new FormData();
    data.append("file", imageFile);

    const response = await api.post("/super/upload/image", data, {
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
      await api.post("/super/items", {
        restaurant_id: restaurant.id,
        category_id: itemForm.category_id,
        name: itemForm.name,
        description: itemForm.description || null,
        price: Number(itemForm.price),
        mrp_price: itemForm.mrp_price === "" ? null : Number(itemForm.mrp_price),
        image_url: imageUrl,
        is_available: itemForm.is_available,
        is_veg: itemForm.is_veg,
        is_special: itemForm.is_special,
        is_bestseller: itemForm.is_bestseller,
        display_order: Number(itemForm.display_order) || 0,
      });

      setItemForm({
        ...emptyItemForm,
        category_id: itemForm.category_id,
      });
      setImageFile(null);
      await loadRestaurant();
      showSuccess("Menu item created");
    } catch (err) {
      console.error("Failed to create item:", err);
      setError(err?.response?.data?.detail || "Failed to create menu item");
    } finally {
      setSubmitting("");
    }
  }

  async function updateItem(itemId) {
    const draft = editDrafts[itemId];
    setSubmitting(itemId);
    setError("");

    try {
      await api.put(`/super/items/${itemId}`, {
        name: draft.name,
        description: draft.description || null,
        price: draft.price === "" ? null : Number(draft.price),
        mrp_price: draft.mrp_price === "" ? null : Number(draft.mrp_price),
        image_url: draft.image_url || null,
        is_available: draft.is_available,
        is_veg: draft.is_veg,
        is_special: draft.is_special,
        is_bestseller: draft.is_bestseller,
      });

      setEditingItemId("");
      await loadRestaurant();
      showSuccess("Menu item updated");
    } catch (err) {
      console.error("Failed to update item:", err);
      setError(err?.response?.data?.detail || "Failed to update menu item");
    } finally {
      setSubmitting("");
    }
  }

  async function deleteItem(itemId) {
    const confirmed = window.confirm("Delete this menu item?");
    if (!confirmed) return;

    setSubmitting(itemId);
    setError("");

    try {
      await api.delete(`/super/items/${itemId}`);
      await loadRestaurant();
      showSuccess("Menu item deleted");
    } catch (err) {
      console.error("Failed to delete item:", err);
      setError(err?.response?.data?.detail || "Failed to delete menu item");
    } finally {
      setSubmitting("");
    }
  }

  async function updateCategory(category) {
    const nextName = window.prompt("Category name", category.name);
    if (!nextName || nextName.trim() === category.name) return;

    setSubmitting(category.id);
    setError("");

    try {
      await api.put(`/super/categories/${category.id}`, {
        name: nextName.trim(),
        icon_emoji: category.icon_emoji || null,
        display_order: category.display_order ?? 0,
      });
      await loadRestaurant();
      showSuccess("Category updated");
    } catch (err) {
      console.error("Failed to update category:", err);
      setError(err?.response?.data?.detail || "Failed to update category");
    } finally {
      setSubmitting("");
    }
  }

  async function deleteCategory(categoryId) {
    const confirmed = window.confirm("Delete this category? Items in this category will also be deleted.");
    if (!confirmed) return;

    setSubmitting(categoryId);
    setError("");

    try {
      await api.delete(`/super/categories/${categoryId}`);
      await loadRestaurant();
      showSuccess("Category deleted");
    } catch (err) {
      console.error("Failed to delete category:", err);
      setError(err?.response?.data?.detail || "Failed to delete category");
    } finally {
      setSubmitting("");
    }
  }

  async function toggleAvailability(item) {
    const draft = editDrafts[item.id] || {};
    setSubmitting(item.id);
    setError("");

    try {
      await api.put(`/super/items/${item.id}`, {
        is_available: !item.is_available,
        name: draft.name || item.name,
        description: draft.description || item.description || null,
        price: draft.price === "" ? item.price : Number(draft.price ?? item.price),
        mrp_price:
          draft.mrp_price === "" || (draft.mrp_price == null && item.mrp_price == null)
            ? null
            : Number(draft.mrp_price ?? item.mrp_price),
        image_url: draft.image_url || item.image_url || null,
        is_veg: draft.is_veg ?? item.is_veg,
        is_special: draft.is_special ?? item.is_special,
        is_bestseller: draft.is_bestseller ?? item.is_bestseller,
      });
      await loadRestaurant();
      showSuccess(item.is_available ? "Item hidden" : "Item available");
    } catch (err) {
      console.error("Failed to update availability:", err);
      setError(err?.response?.data?.detail || "Failed to update availability");
    } finally {
      setSubmitting("");
    }
  }

  async function updateOpenState(isOpen) {
    setSubmitting("open-state");
    setError("");

    try {
      const response = await api.patch(`/super/restaurants/${id}/open-state`, {
        is_open: isOpen,
      });
      setRestaurant(response.data);
      showSuccess(isOpen ? "Restaurant marked open" : "Restaurant marked closed");
    } catch (err) {
      console.error("Failed to update restaurant state:", err);
      setError(err?.response?.data?.detail || "Failed to update restaurant state");
    } finally {
      setSubmitting("");
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="mx-auto max-w-6xl">
          <div className="mb-4 rounded-lg bg-white p-4">
            <div className="mb-2 h-8 w-1/3 rounded bg-gray-200 animate-pulse" />
            <div className="h-4 w-1/4 rounded bg-gray-200 animate-pulse" />
          </div>
          <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
            <div className="h-96 rounded-lg bg-white animate-pulse" />
            <div className="h-96 rounded-lg bg-white animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  if (error && !restaurant) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
        <div className="w-full max-w-sm rounded-lg border border-gray-100 bg-white p-8 text-center shadow-sm">
          <p className="text-lg font-semibold text-gray-950">{error}</p>
          <Link
            to="/super"
            className="mt-4 inline-flex h-10 items-center justify-center rounded-lg bg-black px-4 text-sm font-semibold text-white"
          >
            Back to restaurants
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <DashboardHeader
        eyebrow={
          <Link to="/super" className="text-xs font-semibold uppercase tracking-normal text-orange-700">
            Back to restaurants
          </Link>
        }
        title={restaurant.name}
        subtitle={`${restaurant.city} / ${restaurant.slug}`}
        action={
          <a
            href={`/menu/${restaurant.slug}`}
            className="inline-flex h-10 items-center justify-center rounded-lg bg-black px-4 text-sm font-semibold text-white hover:bg-gray-900"
          >
            View public menu
          </a>
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

        <section className="mb-6 grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-gray-100 bg-white p-4">
            <p className="text-sm font-medium text-gray-500">Categories visible</p>
            <p className="mt-2 text-2xl font-bold text-gray-950">{metrics.categories}</p>
          </div>
          <div className="rounded-lg border border-gray-100 bg-white p-4">
            <p className="text-sm font-medium text-gray-500">Visible items</p>
            <p className="mt-2 text-2xl font-bold text-gray-950">{metrics.items}</p>
          </div>
          <div className="rounded-lg border border-gray-100 bg-white p-4">
            <p className="text-sm font-medium text-gray-500">Specials / bestsellers</p>
            <p className="mt-2 text-2xl font-bold text-gray-950">{metrics.specials}</p>
            <p className="mt-1 text-xs font-medium text-gray-500">{metrics.bestsellers} bestsellers</p>
          </div>
        </section>

        {qr && (
          <section className="mb-6 rounded-lg border border-gray-100 bg-white p-4">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              <img src={qr.qr_image_url} alt="Restaurant QR code" className="h-32 w-32 rounded border border-gray-100" />
              <div className="min-w-0 flex-1">
                <h2 className="font-bold text-gray-950">QR code</h2>
                <p className="mt-1 break-all text-sm text-gray-500">{qr.menu_url}</p>
              </div>
              <button
                type="button"
                onClick={() => downloadImage(qr.qr_image_url, `${restaurant.slug}-qr.png`)}
                className="h-10 rounded-lg border border-gray-200 px-4 text-sm font-semibold text-gray-900 hover:bg-gray-50"
              >
                Download QR
              </button>
              <button
                type="button"
                disabled={submitting === "open-state"}
                onClick={() => updateOpenState(restaurant.is_open === false)}
                className={`h-10 rounded-lg px-4 text-sm font-semibold disabled:opacity-50 ${
                  restaurant.is_open === false
                    ? "bg-green-600 text-white hover:bg-green-700"
                    : "bg-red-600 text-white hover:bg-red-700"
                }`}
              >
                {restaurant.is_open === false ? "Mark open" : "Mark closed"}
              </button>
            </div>
          </section>
        )}

        <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <aside className="space-y-4">
            <form onSubmit={createCategory} className="rounded-lg border border-gray-100 bg-white p-4">
              <h2 className="text-base font-bold text-gray-950">Add category</h2>
              <div className="mt-4 space-y-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Name</label>
                  <input
                    type="text"
                    value={categoryForm.name}
                    onChange={(event) =>
                      setCategoryForm((current) => ({ ...current, name: event.target.value }))
                    }
                    required
                    className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                    placeholder="Starters"
                  />
                </div>
                <div className="grid grid-cols-[1fr_96px] gap-3">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Icon</label>
                    <input
                      type="text"
                      value={categoryForm.icon_emoji}
                      onChange={(event) =>
                        setCategoryForm((current) => ({ ...current, icon_emoji: event.target.value }))
                      }
                      className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                      placeholder="Food"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Order</label>
                    <input
                      type="number"
                      value={categoryForm.display_order}
                      onChange={(event) =>
                        setCategoryForm((current) => ({ ...current, display_order: event.target.value }))
                      }
                      className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                    />
                  </div>
                </div>
              </div>
              <button
                type="submit"
                disabled={submitting === "category"}
                className="mt-4 h-10 w-full rounded-lg bg-black px-4 text-sm font-semibold text-white hover:bg-gray-900 disabled:opacity-50"
              >
                {submitting === "category" ? "Creating..." : "Create category"}
              </button>
            </form>

            <form onSubmit={createItem} className="rounded-lg border border-gray-100 bg-white p-4">
              <h2 className="text-base font-bold text-gray-950">Add menu item</h2>
              <div className="mt-4 space-y-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Category</label>
                  <select
                    value={itemForm.category_id}
                    onChange={(event) =>
                      setItemForm((current) => ({ ...current, category_id: event.target.value }))
                    }
                    required
                    className="h-10 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm outline-none focus:border-gray-400"
                  >
                    <option value="">Select category</option>
                    {categories.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Item name</label>
                  <input
                    type="text"
                    value={itemForm.name}
                    onChange={(event) =>
                      setItemForm((current) => ({ ...current, name: event.target.value }))
                    }
                    required
                    className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                    placeholder="Paneer roll"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
                  <textarea
                    value={itemForm.description}
                    onChange={(event) =>
                      setItemForm((current) => ({ ...current, description: event.target.value }))
                    }
                    rows="3"
                    className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-gray-400"
                    placeholder="Short customer-facing description"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Price</label>
                    <input
                      type="number"
                      min="0"
                      value={itemForm.price}
                      onChange={(event) =>
                        setItemForm((current) => ({ ...current, price: event.target.value }))
                      }
                      required
                      className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">MRP</label>
                    <input
                      type="number"
                      min="0"
                      value={itemForm.mrp_price}
                      onChange={(event) =>
                        setItemForm((current) => ({ ...current, mrp_price: event.target.value }))
                      }
                      className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                    />
                  </div>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Image URL</label>
                  <input
                    type="url"
                    value={itemForm.image_url}
                    onChange={(event) =>
                      setItemForm((current) => ({ ...current, image_url: event.target.value }))
                    }
                    className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                    placeholder="https://..."
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Upload image</label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(event) => setImageFile(event.target.files?.[0] || null)}
                    className="block w-full text-sm text-gray-600 file:mr-3 file:h-9 file:rounded-lg file:border-0 file:bg-gray-100 file:px-3 file:text-sm file:font-semibold file:text-gray-900"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <input
                      type="checkbox"
                      checked={itemForm.is_veg}
                      onChange={(event) =>
                        setItemForm((current) => ({ ...current, is_veg: event.target.checked }))
                      }
                    />
                    Veg
                  </label>
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <input
                      type="checkbox"
                      checked={itemForm.is_special}
                      onChange={(event) =>
                        setItemForm((current) => ({ ...current, is_special: event.target.checked }))
                      }
                    />
                    Special
                  </label>
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <input
                      type="checkbox"
                      checked={itemForm.is_bestseller}
                      onChange={(event) =>
                        setItemForm((current) => ({ ...current, is_bestseller: event.target.checked }))
                      }
                    />
                    Bestseller
                  </label>
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <input
                      type="checkbox"
                      checked={itemForm.is_available}
                      onChange={(event) =>
                        setItemForm((current) => ({ ...current, is_available: event.target.checked }))
                      }
                    />
                    Available
                  </label>
                  <div>
                    <label className="mb-1 block text-sm font-medium text-gray-700">Order</label>
                    <input
                      type="number"
                      value={itemForm.display_order}
                      onChange={(event) =>
                        setItemForm((current) => ({ ...current, display_order: event.target.value }))
                      }
                      className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                    />
                  </div>
                </div>
              </div>
              <button
                type="submit"
                disabled={submitting === "item" || categories.length === 0}
                className="mt-4 h-10 w-full rounded-lg bg-black px-4 text-sm font-semibold text-white hover:bg-gray-900 disabled:opacity-50"
              >
                {submitting === "item" ? "Creating..." : "Create item"}
              </button>
            </form>
          </aside>

          <section className="space-y-4">
            <div className="rounded-lg border border-gray-100 bg-white p-4">
              <h2 className="text-base font-bold text-gray-950">Visible public menu</h2>
              <p className="mt-1 text-sm text-gray-500">
                This preview uses the public menu endpoint, including unavailable item states.
              </p>
            </div>

            {managementMenu.length === 0 ? (
              <div className="rounded-lg border border-gray-100 bg-white p-8 text-center">
                <p className="font-semibold text-gray-950">No visible categories yet</p>
                <p className="mt-1 text-sm text-gray-500">
                  Create a category, then add an available item to publish it on the public menu.
                </p>
              </div>
            ) : (
              managementMenu.map((category) => (
                <div key={category.id} className="space-y-3">
                  <div className="rounded-lg border border-gray-100 bg-white">
                    <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
                      <div>
                        <h2 className="font-bold text-gray-950">{category.name}</h2>
                        <p className="text-sm text-gray-500">{category.items.length} items</p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => updateCategory(category)}
                          className="rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-gray-900 hover:bg-gray-50"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => deleteCategory(category.id)}
                          className="rounded-lg border border-red-200 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-50"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                    <CategorySection category={category} />
                  </div>

                  <div className="rounded-lg border border-gray-100 bg-white">
                    <div className="border-b border-gray-100 px-4 py-3">
                      <h3 className="text-sm font-bold text-gray-950">Manage {category.name}</h3>
                    </div>
                    <div className="divide-y divide-gray-100">
                      {category.items.map((item) => {
                        const draft = editDrafts[item.id] || {};
                        const isEditing = editingItemId === item.id;

                        return (
                          <div key={item.id} className="p-4">
                            {isEditing ? (
                              <div className="grid gap-3 md:grid-cols-[1fr_120px_120px_auto] md:items-end">
                                <div>
                                  <label className="mb-1 block text-xs font-medium text-gray-600">Name</label>
                                  <input
                                    value={draft.name || ""}
                                    onChange={(event) =>
                                      setEditDrafts((current) => ({
                                        ...current,
                                        [item.id]: { ...draft, name: event.target.value },
                                      }))
                                    }
                                    className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                                  />
                                </div>
                                <div className="md:col-span-4">
                                  <label className="mb-1 block text-xs font-medium text-gray-600">Description</label>
                                  <textarea
                                    value={draft.description || ""}
                                    onChange={(event) =>
                                      setEditDrafts((current) => ({
                                        ...current,
                                        [item.id]: { ...draft, description: event.target.value },
                                      }))
                                    }
                                    rows="2"
                                    className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm outline-none focus:border-gray-400"
                                  />
                                </div>
                                <div className="md:col-span-4">
                                  <label className="mb-1 block text-xs font-medium text-gray-600">Image URL</label>
                                  <input
                                    type="url"
                                    value={draft.image_url || ""}
                                    onChange={(event) =>
                                      setEditDrafts((current) => ({
                                        ...current,
                                        [item.id]: { ...draft, image_url: event.target.value },
                                      }))
                                    }
                                    className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                                  />
                                </div>
                                <div>
                                  <label className="mb-1 block text-xs font-medium text-gray-600">Price</label>
                                  <input
                                    type="number"
                                    min="0"
                                    value={draft.price ?? ""}
                                    onChange={(event) =>
                                      setEditDrafts((current) => ({
                                        ...current,
                                        [item.id]: { ...draft, price: event.target.value },
                                      }))
                                    }
                                    className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                                  />
                                </div>
                                <div>
                                  <label className="mb-1 block text-xs font-medium text-gray-600">MRP</label>
                                  <input
                                    type="number"
                                    min="0"
                                    value={draft.mrp_price ?? ""}
                                    onChange={(event) =>
                                      setEditDrafts((current) => ({
                                        ...current,
                                        [item.id]: { ...draft, mrp_price: event.target.value },
                                      }))
                                    }
                                    className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-gray-400"
                                  />
                                </div>
                                <div className="flex gap-2">
                                  <button
                                    type="button"
                                    onClick={() => updateItem(item.id)}
                                    disabled={submitting === item.id}
                                    className="h-10 rounded-lg bg-black px-3 text-xs font-semibold text-white hover:bg-gray-900 disabled:opacity-50"
                                  >
                                    Save
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setEditingItemId("")}
                                    className="h-10 rounded-lg border border-gray-200 px-3 text-xs font-semibold text-gray-900 hover:bg-gray-50"
                                  >
                                    Cancel
                                  </button>
                                </div>
                                <div className="flex gap-4 md:col-span-4">
                                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                                    <input
                                      type="checkbox"
                                      checked={Boolean(draft.is_available)}
                                      onChange={(event) =>
                                        setEditDrafts((current) => ({
                                          ...current,
                                          [item.id]: { ...draft, is_available: event.target.checked },
                                        }))
                                      }
                                    />
                                    Available
                                  </label>
                                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                                    <input
                                      type="checkbox"
                                      checked={Boolean(draft.is_veg)}
                                      onChange={(event) =>
                                        setEditDrafts((current) => ({
                                          ...current,
                                          [item.id]: { ...draft, is_veg: event.target.checked },
                                        }))
                                      }
                                    />
                                    Veg
                                  </label>
                                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                                    <input
                                      type="checkbox"
                                      checked={Boolean(draft.is_special)}
                                      onChange={(event) =>
                                        setEditDrafts((current) => ({
                                          ...current,
                                          [item.id]: { ...draft, is_special: event.target.checked },
                                        }))
                                      }
                                    />
                                    Special
                                  </label>
                                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
                                    <input
                                      type="checkbox"
                                      checked={Boolean(draft.is_bestseller)}
                                      onChange={(event) =>
                                        setEditDrafts((current) => ({
                                          ...current,
                                          [item.id]: { ...draft, is_bestseller: event.target.checked },
                                        }))
                                      }
                                    />
                                    Bestseller
                                  </label>
                                </div>
                              </div>
                            ) : (
                              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <div>
                                  <p className="font-semibold text-gray-950">{item.name}</p>
                                  <p className="mt-1 text-sm text-gray-500">
                                    {formatPrice(item.price)}
                                    {item.is_special ? " / Special" : ""}
                                    {item.is_bestseller ? " / Bestseller" : ""}
                                    {item.is_veg ? " / Veg" : " / Non-veg"}
                                    {item.is_available ? "" : " / Hidden"}
                                  </p>
                                </div>
                                <div className="flex gap-2">
                                  <button
                                    type="button"
                                    onClick={() => toggleAvailability(item)}
                                    className="h-9 rounded-lg border border-gray-200 px-3 text-xs font-semibold text-gray-900 hover:bg-gray-50"
                                  >
                                    {item.is_available ? "Hide" : "Show"}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setEditingItemId(item.id)}
                                    className="h-9 rounded-lg border border-gray-200 px-3 text-xs font-semibold text-gray-900 hover:bg-gray-50"
                                  >
                                    Edit
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => deleteItem(item.id)}
                                    disabled={submitting === item.id}
                                    className="h-9 rounded-lg border border-red-200 px-3 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
                                  >
                                    Delete
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
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
