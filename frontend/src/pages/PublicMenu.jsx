import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import api, { DEFAULT_API_BASE_URL } from "../api/axios";
import CategorySection from "../components/CategorySection";

const MENU_FETCH_RETRIES = 2;
const MENU_RETRY_DELAY_MS = 900;

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function shouldRetryMenuFetch(error, attempt) {
  if (attempt >= MENU_FETCH_RETRIES) return false;

  const status = error?.response?.status;

  return (
    !status ||
    status === 408 ||
    status === 429 ||
    status >= 500
  );
}

function getMenuErrorMessage(error) {
  if (error?.response?.status === 503) {
    return "Menu service is waking up. Please try again.";
  }

  if (error?.userMessage) {
    return error.userMessage;
  }

  return error?.response?.data?.detail || "Menu not found";
}

async function fetchPublicMenu(slug) {
  const encodedSlug = encodeURIComponent(slug);

  try {
    return await api.get(`/menu/${encodedSlug}`);
  } catch (error) {
    const primaryBaseUrl = api.defaults.baseURL?.replace(/\/+$/, "");

    if (!error.response && primaryBaseUrl !== DEFAULT_API_BASE_URL) {
      return axios.get(
        `${DEFAULT_API_BASE_URL}/menu/${encodedSlug}`,
        {
          timeout: 30000,
        }
      );
    }

    throw error;
  }
}

export default function PublicMenu() {
  const { slug } = useParams();
  const [menuData, setMenuData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [logoFailed, setLogoFailed] = useState(false);
  const [activeCategory, setActiveCategory] = useState(0);
  const [searchTerm, setSearchTerm] = useState("");
  const categoryRefs = useRef([]);

  useEffect(() => {
    let mounted = true;

    async function fetchMenu() {
      setError("");
      setLoading(true);
      setActiveCategory(0);
      setSearchTerm("");

      for (let attempt = 0; attempt <= MENU_FETCH_RETRIES; attempt += 1) {
        try {
          const response = await fetchPublicMenu(slug);
          if (mounted) {
            setLogoFailed(false);
            setMenuData(response.data);
            setLoading(false);
          }
          return;
        } catch (error) {
          console.error("Failed to load menu:", error);

          if (shouldRetryMenuFetch(error, attempt)) {
            await wait(MENU_RETRY_DELAY_MS * (attempt + 1));
            if (!mounted) return;
            continue;
          }

          if (mounted) {
            setError(getMenuErrorMessage(error));
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
  }, [slug]);

  useEffect(() => {
    if (!menuData?.menu?.length) return undefined;

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
        rootMargin: "-150px 0px -55% 0px",
        threshold: [0.15, 0.35, 0.6],
      }
    );

    categoryRefs.current.forEach((section) => {
      if (section) observer.observe(section);
    });

    return () => observer.disconnect();
  }, [menuData]);

  const filteredMenu = useMemo(() => {
    const menu = menuData?.menu || [];
    const query = searchTerm.trim().toLowerCase();

    if (!query) return menu;

    return menu
      .map((category) => ({
        ...category,
        items: (category.items || []).filter((item) => {
          const searchable = `${item.name || ""} ${item.description || ""}`.toLowerCase();
          return searchable.includes(query);
        }),
      }))
      .filter((category) => category.items.length > 0);
  }, [menuData, searchTerm]);

  const totalItems = useMemo(
    () => (menuData?.menu || []).reduce((count, category) => count + (category.items || []).length, 0),
    [menuData]
  );

  const visibleItems = useMemo(
    () => filteredMenu.reduce((count, category) => count + (category.items || []).length, 0),
    [filteredMenu]
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f6f7f9]">
        <div className="sticky top-0 z-20 border-b border-zinc-200 bg-white/95 px-4 py-4 backdrop-blur">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-center gap-3">
              <div className="h-14 w-14 rounded-lg bg-zinc-200 animate-pulse" />
              <div className="flex-1">
                <div className="h-6 w-1/2 rounded bg-zinc-200 animate-pulse" />
                <div className="mt-2 h-4 w-1/3 rounded bg-zinc-200 animate-pulse" />
              </div>
            </div>
          </div>
        </div>

        <div className="border-b border-zinc-200 bg-white px-4 py-3">
          <div className="mx-auto max-w-3xl">
            <div className="h-11 rounded-lg bg-zinc-200 animate-pulse" />
          </div>
        </div>

        <div className="sticky top-[89px] z-10 border-b border-zinc-200 bg-white px-4 py-3">
          <div className="mx-auto flex max-w-3xl gap-2 overflow-hidden">
            {[1, 2, 3].map((item) => (
              <div key={item} className="h-9 w-24 flex-shrink-0 rounded-full bg-zinc-200 animate-pulse" />
            ))}
          </div>
        </div>

        <div className="mx-auto max-w-3xl space-y-4 p-4">
          {[1, 2, 3].map((s) => (
            <div key={s} className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
              <div className="mb-3 h-6 w-1/2 rounded bg-zinc-200 animate-pulse" />
              <div className="space-y-4">
                {[1, 2].map((i) => (
                  <div key={i} className="flex gap-3">
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
        <div className="w-full max-w-sm rounded-lg border border-zinc-200 bg-white p-8 text-center shadow-sm">
          <p className="text-lg font-semibold text-zinc-950">{error || "Menu not found"}</p>
          <p className="mt-2 text-sm text-zinc-500">Please check the restaurant link or try again later.</p>
        </div>
      </div>
    );
  }

  const scrollToCategory = (index) => {
    setActiveCategory(index);
    if (categoryRefs.current[index]) {
      categoryRefs.current[index].scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  };

  return (
    <div className="min-h-screen bg-[#f6f7f9] text-zinc-950">
      <header className="sticky top-0 z-20 border-b border-zinc-200 bg-white/95 backdrop-blur">
        <div className="mx-auto max-w-3xl px-4 py-4">
          <div className="flex items-center gap-3">
            {menuData.restaurant.logo_url && !logoFailed ? (
              <img
                src={menuData.restaurant.logo_url}
                alt={menuData.restaurant.name}
                referrerPolicy="no-referrer"
                onError={() => setLogoFailed(true)}
                className="h-14 w-14 rounded-lg border border-zinc-200 object-cover shadow-sm"
              />
            ) : (
              <div className="flex h-14 w-14 items-center justify-center rounded-lg border border-zinc-200 bg-zinc-950 text-lg font-bold text-white shadow-sm">
                {menuData.restaurant.name?.[0] || "R"}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-xl font-bold text-zinc-950">{menuData.restaurant.name}</h1>
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs font-medium text-zinc-500">
                <span>{menuData.restaurant.city || "Menu"}</span>
                <span className="h-1 w-1 rounded-full bg-zinc-300" />
                <span>{totalItems} {totalItems === 1 ? "item" : "items"}</span>
              </div>
              <span
                className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                  menuData.restaurant.is_open === false
                    ? "bg-red-50 text-red-700"
                    : "bg-emerald-50 text-emerald-700"
                }`}
              >
                {menuData.restaurant.is_open === false ? "Closed" : "Open now"}
              </span>
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

      <div className="border-b border-zinc-200 bg-white px-4 py-3">
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
              className="h-11 w-full rounded-lg border border-zinc-200 bg-zinc-50 pl-10 pr-4 text-sm font-medium text-zinc-950 outline-none transition focus:border-zinc-400 focus:bg-white"
            />
          </div>
        </div>
      </div>

      {filteredMenu.length > 0 && (
        <div className="sticky top-[89px] z-10 overflow-x-auto border-b border-zinc-200 bg-white/95 backdrop-blur">
          <div className="mx-auto flex max-w-3xl gap-2 px-4">
            {filteredMenu.map((category, idx) => (
              <button
                key={category.id}
                onClick={() => scrollToCategory(idx)}
                className={`whitespace-nowrap border-b-2 px-3 py-3 text-sm font-semibold transition-colors ${
                  activeCategory === idx
                    ? "border-zinc-950 text-zinc-950"
                    : "border-transparent text-zinc-500 hover:text-zinc-950"
                }`}
              >
                {category.icon_emoji && <span className="mr-1">{category.icon_emoji}</span>}
                {category.name}
              </button>
            ))}
          </div>
        </div>
      )}

      <main className="mx-auto max-w-3xl px-4 py-5">
        {menuData.menu.length === 0 ? (
          <div className="rounded-lg border border-zinc-200 bg-white p-8 text-center shadow-sm">
            <p className="font-semibold text-zinc-950">No items available right now</p>
            <p className="mt-2 text-sm text-zinc-500">Please check back soon or ask the restaurant staff for today's specials.</p>
          </div>
        ) : filteredMenu.length === 0 ? (
          <div className="rounded-lg border border-zinc-200 bg-white p-8 text-center shadow-sm">
            <p className="font-semibold text-zinc-950">No matching dishes</p>
            <p className="mt-2 text-sm text-zinc-500">No results for "{searchTerm.trim()}"</p>
            <button
              type="button"
              onClick={() => setSearchTerm("")}
              className="mt-4 rounded-full bg-zinc-950 px-4 py-2 text-sm font-semibold text-white"
            >
              Clear search
            </button>
          </div>
        ) : (
          <div className="space-y-5 pb-10">
            {searchTerm.trim() && (
              <p className="text-sm font-medium text-zinc-500">
                {visibleItems} {visibleItems === 1 ? "result" : "results"} for "{searchTerm.trim()}"
              </p>
            )}
            {filteredMenu.map((category, idx) => (
              <section
                key={category.id}
                ref={(el) => (categoryRefs.current[idx] = el)}
                data-index={idx}
                className="scroll-mt-36"
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
