import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { API_BASE_URL_CANDIDATES } from "../api/axios";
import CategorySection from "../components/CategorySection";
import MenuItemCard from "../components/MenuItemCard";

const MENU_FETCH_RETRIES = 2;
const MENU_RETRY_DELAY_MS = 900;

const MENU_FILTERS = [
  { id: "all", label: "All dishes" },
  { id: "veg", label: "Veg" },
  { id: "specials", label: "Specials" },
];

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRecoverableMenuError(error) {
  const status = error?.response?.status;

  return (
    !status ||
    status === 408 ||
    status === 429 ||
    status >= 500
  );
}

function shouldRetryMenuFetch(error, attempt) {
  return attempt < MENU_FETCH_RETRIES && isRecoverableMenuError(error);
}

function getMenuErrorMessage(error) {
  const status = error?.response?.status;

  if (status === 403) {
    return "This restaurant is not accepting public menu views right now.";
  }

  if (status === 404) {
    return "This QR menu link does not match an active restaurant.";
  }

  if (status === 503) {
    return "The menu is temporarily syncing. Please retry in a moment.";
  }

  if (error?.userMessage) {
    return error.userMessage;
  }

  return error?.response?.data?.detail || "Menu not found";
}

async function fetchPublicMenu(slug) {
  const encodedSlug = encodeURIComponent(slug || "");
  let lastError = null;

  for (const baseUrl of API_BASE_URL_CANDIDATES) {
    try {
      return await axios.get(
        `${baseUrl}/menu/${encodedSlug}`,
        {
          timeout: 30000,
        }
      );
    } catch (error) {
      lastError = error;

      if (!isRecoverableMenuError(error)) {
        throw error;
      }
    }
  }

  throw lastError;
}

function itemMatchesFilter(item, activeFilter) {
  if (activeFilter === "veg") return Boolean(item.is_veg);
  if (activeFilter === "specials") return Boolean(item.is_special || item.is_bestseller);

  return true;
}

function itemMatchesSearch(item, query) {
  if (!query) return true;

  const searchable = `${item.name || ""} ${item.description || ""}`.toLowerCase();

  return searchable.includes(query);
}

function getFilterEmptyCopy(activeFilter) {
  if (activeFilter === "veg") return "No vegetarian dishes match this view.";
  if (activeFilter === "specials") return "No specials are visible right now.";

  return "No matching dishes";
}

export default function PublicMenu() {
  const { slug } = useParams();
  const [menuData, setMenuData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [logoFailed, setLogoFailed] = useState(false);
  const [activeCategory, setActiveCategory] = useState(0);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeFilter, setActiveFilter] = useState("all");
  const [retrySeed, setRetrySeed] = useState(0);
  const categoryRefs = useRef([]);

  useEffect(() => {
    let mounted = true;

    async function fetchMenu() {
      setError("");
      setLoading(true);
      setActiveCategory(0);
      setSearchTerm("");
      setActiveFilter("all");
      categoryRefs.current = [];

      for (let attempt = 0; attempt <= MENU_FETCH_RETRIES; attempt += 1) {
        try {
          const response = await fetchPublicMenu(slug);
          if (mounted) {
            setLogoFailed(false);
            setMenuData(response.data);
            setLoading(false);
          }
          return;
        } catch (fetchError) {
          console.error("Failed to load menu:", fetchError);

          if (shouldRetryMenuFetch(fetchError, attempt)) {
            await wait(MENU_RETRY_DELAY_MS * (attempt + 1));
            if (!mounted) return;
            continue;
          }

          if (mounted) {
            setError(getMenuErrorMessage(fetchError));
            setMenuData(null);
            setLoading(false);
          }
          return;
        }
      }
    }

    fetchMenu();
    return () => {
      mounted = false;
    };
  }, [slug, retrySeed]);

  const filteredMenu = useMemo(() => {
    const menu = menuData?.menu || [];
    const query = searchTerm.trim().toLowerCase();

    return menu
      .map((category) => ({
        ...category,
        items: (category.items || []).filter((item) => (
          itemMatchesSearch(item, query) && itemMatchesFilter(item, activeFilter)
        )),
      }))
      .filter((category) => category.items.length > 0);
  }, [activeFilter, menuData, searchTerm]);

  const totalItems = useMemo(
    () => (menuData?.menu || []).reduce((count, category) => count + (category.items || []).length, 0),
    [menuData]
  );

  const visibleItems = useMemo(
    () => filteredMenu.reduce((count, category) => count + (category.items || []).length, 0),
    [filteredMenu]
  );

  const featuredItems = useMemo(
    () => (menuData?.menu || [])
      .flatMap((category) => (
        (category.items || []).map((item) => ({
          ...item,
          category_name: category.name,
        }))
      ))
      .filter((item) => item.is_special || item.is_bestseller)
      .slice(0, 4),
    [menuData]
  );

  useEffect(() => {
    if (!filteredMenu.length) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        const visibleEntry = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

        if (visibleEntry?.target?.dataset?.index) {
          setActiveCategory(Number(visibleEntry.target.dataset.index));
        }
      },
      {
        rootMargin: "-160px 0px -55% 0px",
        threshold: [0.15, 0.35, 0.6],
      }
    );

    categoryRefs.current.forEach((section) => {
      if (section) observer.observe(section);
    });

    return () => observer.disconnect();
  }, [filteredMenu]);

  const scrollToCategory = (index) => {
    setActiveCategory(index);
    categoryRefs.current[index]?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };

  const resetFilters = () => {
    setSearchTerm("");
    setActiveFilter("all");
    setActiveCategory(0);
    categoryRefs.current = [];
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f6f7f9]">
        <div className="border-b border-zinc-200 bg-white px-4 py-5">
          <div className="mx-auto max-w-3xl">
            <div className="flex items-center gap-3">
              <div className="h-16 w-16 rounded-lg bg-zinc-200 animate-pulse" />
              <div className="flex-1">
                <div className="h-6 w-1/2 rounded bg-zinc-200 animate-pulse" />
                <div className="mt-2 h-4 w-1/3 rounded bg-zinc-200 animate-pulse" />
              </div>
            </div>
          </div>
        </div>

        <div className="sticky top-0 z-20 border-b border-zinc-200 bg-white px-4 py-3">
          <div className="mx-auto max-w-3xl space-y-3">
            <div className="h-11 rounded-lg bg-zinc-200 animate-pulse" />
            <div className="flex gap-2 overflow-hidden">
              {[1, 2, 3].map((item) => (
                <div key={item} className="h-9 w-24 flex-shrink-0 rounded-full bg-zinc-200 animate-pulse" />
              ))}
            </div>
          </div>
        </div>

        <div className="mx-auto max-w-3xl space-y-4 p-4">
          {[1, 2, 3].map((section) => (
            <div key={section} className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
              <div className="mb-3 h-6 w-1/2 rounded bg-zinc-200 animate-pulse" />
              <div className="space-y-4">
                {[1, 2].map((item) => (
                  <div key={item} className="flex gap-3">
                    <div className="flex-1">
                      <div className="mb-2 h-4 w-3/4 rounded bg-zinc-200 animate-pulse" />
                      <div className="mb-2 h-3 w-1/3 rounded bg-zinc-200 animate-pulse" />
                      <div className="h-3 w-5/6 rounded bg-zinc-200 animate-pulse" />
                    </div>
                    <div className="h-24 w-24 rounded-lg bg-zinc-200 animate-pulse" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!menuData || error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f6f7f9] p-4">
        <div className="w-full max-w-sm rounded-lg border border-zinc-200 bg-white p-6 text-center shadow-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-red-50 text-lg font-bold text-red-700">
            !
          </div>
          <p className="mt-4 text-lg font-semibold text-zinc-950">{error || "Menu not found"}</p>
          <p className="mt-2 text-sm leading-5 text-zinc-500">
            Try again from this QR. If it keeps failing, ask the restaurant staff to refresh the menu link.
          </p>
          <button
            type="button"
            onClick={() => setRetrySeed((current) => current + 1)}
            className="mt-5 h-10 rounded-lg bg-zinc-950 px-4 text-sm font-semibold text-white hover:bg-zinc-800"
          >
            Retry menu
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f6f7f9] text-zinc-950">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto max-w-3xl px-4 py-5">
          <div className="flex items-start gap-3">
            {menuData.restaurant.logo_url && !logoFailed ? (
              <img
                src={menuData.restaurant.logo_url}
                alt={menuData.restaurant.name}
                referrerPolicy="no-referrer"
                onError={() => setLogoFailed(true)}
                className="h-16 w-16 rounded-lg border border-zinc-200 object-cover shadow-sm"
              />
            ) : (
              <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-lg border border-zinc-200 bg-zinc-950 text-xl font-bold text-white shadow-sm">
                {menuData.restaurant.name?.[0] || "R"}
              </div>
            )}

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-2xl font-bold text-zinc-950">{menuData.restaurant.name}</h1>
                <span
                  className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                    menuData.restaurant.is_open === false
                      ? "bg-red-50 text-red-700"
                      : "bg-emerald-50 text-emerald-700"
                  }`}
                >
                  {menuData.restaurant.is_open === false ? "Closed" : "Open now"}
                </span>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs font-medium text-zinc-500">
                <span>{menuData.restaurant.city || "Digital menu"}</span>
                <span className="h-1 w-1 rounded-full bg-zinc-300" />
                <span>{totalItems} {totalItems === 1 ? "dish" : "dishes"}</span>
                <span className="h-1 w-1 rounded-full bg-zinc-300" />
                <span>Live QR menu</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {menuData.restaurant.is_open === false && (
        <div className="border-b border-red-100 bg-red-50 px-4 py-3">
          <p className="mx-auto max-w-3xl text-sm font-medium text-red-800">
            This restaurant is currently closed. You can still browse the menu.
          </p>
        </div>
      )}

      <section className="sticky top-0 z-20 border-b border-zinc-200 bg-white/95 px-4 py-3 backdrop-blur">
        <div className="mx-auto max-w-3xl">
          <div className="relative">
            <svg
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="m21 21-4.35-4.35" />
              <circle cx="11" cy="11" r="7" />
            </svg>
            <input
              type="search"
              value={searchTerm}
              onChange={(event) => {
                setSearchTerm(event.target.value);
                setActiveCategory(0);
                categoryRefs.current = [];
              }}
              placeholder="Search dishes"
              className="h-11 w-full rounded-lg border border-zinc-200 bg-zinc-50 pl-10 pr-10 text-sm font-medium text-zinc-950 outline-none transition focus:border-zinc-400 focus:bg-white"
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => setSearchTerm("")}
                className="absolute right-2 top-1/2 h-8 w-8 -translate-y-1/2 rounded-lg text-sm font-bold text-zinc-500 hover:bg-zinc-100"
                aria-label="Clear search"
              >
                x
              </button>
            )}
          </div>

          <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
            {MENU_FILTERS.map((filter) => (
              <button
                key={filter.id}
                type="button"
                onClick={() => {
                  setActiveFilter(filter.id);
                  setActiveCategory(0);
                  categoryRefs.current = [];
                }}
                className={`h-9 flex-shrink-0 rounded-full border px-3 text-sm font-semibold transition ${
                  activeFilter === filter.id
                    ? "border-zinc-950 bg-zinc-950 text-white"
                    : "border-zinc-200 bg-white text-zinc-700 hover:border-zinc-400"
                }`}
              >
                {filter.label}
              </button>
            ))}
          </div>

          {filteredMenu.length > 0 && (
            <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
              {filteredMenu.map((category, idx) => (
                <button
                  key={category.id}
                  type="button"
                  onClick={() => scrollToCategory(idx)}
                  className={`h-9 flex-shrink-0 rounded-full border px-3 text-sm font-semibold transition ${
                    activeCategory === idx
                      ? "border-orange-600 bg-orange-50 text-orange-800"
                      : "border-zinc-200 bg-white text-zinc-600 hover:border-zinc-400 hover:text-zinc-950"
                  }`}
                >
                  {category.icon_emoji && <span className="mr-1">{category.icon_emoji}</span>}
                  {category.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      <main className="mx-auto max-w-3xl px-4 py-5">
        {menuData.menu.length === 0 ? (
          <div className="rounded-lg border border-zinc-200 bg-white p-8 text-center shadow-sm">
            <p className="font-semibold text-zinc-950">No items available right now</p>
            <p className="mt-2 text-sm text-zinc-500">Please check back soon or ask the restaurant staff for today's specials.</p>
          </div>
        ) : filteredMenu.length === 0 ? (
          <div className="rounded-lg border border-zinc-200 bg-white p-8 text-center shadow-sm">
            <p className="font-semibold text-zinc-950">{getFilterEmptyCopy(activeFilter)}</p>
            {searchTerm.trim() && (
              <p className="mt-2 text-sm text-zinc-500">No results for "{searchTerm.trim()}"</p>
            )}
            <button
              type="button"
              onClick={resetFilters}
              className="mt-4 h-10 rounded-lg bg-zinc-950 px-4 text-sm font-semibold text-white hover:bg-zinc-800"
            >
              Show all dishes
            </button>
          </div>
        ) : (
          <div className="space-y-5 pb-10">
            {(searchTerm.trim() || activeFilter !== "all") && (
              <p className="text-sm font-medium text-zinc-500">
                Showing {visibleItems} of {totalItems} {totalItems === 1 ? "dish" : "dishes"}
              </p>
            )}

            {featuredItems.length > 0 && !searchTerm.trim() && activeFilter === "all" && (
              <section className="rounded-lg border border-orange-100 bg-orange-50/60 p-3">
                <div className="mb-1 flex items-center justify-between px-1">
                  <h2 className="text-sm font-bold text-orange-950">Featured picks</h2>
                  <span className="text-xs font-semibold text-orange-700">{featuredItems.length} highlighted</span>
                </div>
                <div className="rounded-lg border border-orange-100 bg-white px-3">
                  {featuredItems.map((item) => (
                    <MenuItemCard
                      key={`featured-${item.id}`}
                      item={item}
                    />
                  ))}
                </div>
              </section>
            )}

            {filteredMenu.map((category, idx) => (
              <section
                key={category.id}
                ref={(el) => (categoryRefs.current[idx] = el)}
                data-index={idx}
                className="scroll-mt-44"
              >
                <CategorySection category={category} />
              </section>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
