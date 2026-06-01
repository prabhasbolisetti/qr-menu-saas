import { useEffect, useState, useRef } from "react";
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
  try {
    return await api.get(`/menu/${slug}`);
  } catch (error) {
    const primaryBaseUrl = api.defaults.baseURL?.replace(/\/+$/, "");

    if (!error.response && primaryBaseUrl !== DEFAULT_API_BASE_URL) {
      return axios.get(
        `${DEFAULT_API_BASE_URL}/menu/${encodeURIComponent(slug)}`,
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
  const categoryRefs = useRef([]);

  useEffect(() => {
    let mounted = true;

    async function fetchMenu() {
      setError("");
      setLoading(true);

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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="sticky top-0 z-20 border-b border-gray-100 bg-white px-4 py-4">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-center gap-3">
              <div className="h-14 w-14 rounded-lg bg-gray-200 animate-pulse" />
              <div className="flex-1">
                <div className="h-6 w-1/2 rounded bg-gray-200 animate-pulse" />
                <div className="mt-2 h-4 w-1/3 rounded bg-gray-200 animate-pulse" />
              </div>
            </div>
          </div>
        </div>

        <div className="sticky top-[89px] z-10 border-b border-gray-100 bg-white px-4 py-3">
          <div className="mx-auto flex max-w-3xl gap-2 overflow-hidden">
            {[1, 2, 3].map((item) => (
              <div key={item} className="h-9 w-24 flex-shrink-0 rounded-full bg-gray-200 animate-pulse" />
            ))}
          </div>
        </div>

        <div className="mx-auto max-w-3xl space-y-4 p-4">
          {[1, 2, 3].map((s) => (
            <div key={s} className="rounded-lg border border-gray-100 bg-white p-4">
              <div className="mb-3 h-6 w-1/2 rounded bg-gray-200 animate-pulse" />
              <div className="space-y-4">
                {[1, 2].map((i) => (
                  <div key={i} className="flex gap-3">
                    <div className="flex-1">
                      <div className="mb-2 h-4 w-3/4 rounded bg-gray-200 animate-pulse" />
                      <div className="mb-2 h-3 w-1/3 rounded bg-gray-200 animate-pulse" />
                      <div className="h-3 w-5/6 rounded bg-gray-200 animate-pulse" />
                    </div>
                    <div className="h-24 w-24 rounded-lg bg-gray-200 animate-pulse" />
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
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
        <div className="w-full max-w-sm rounded-lg border border-gray-100 bg-white p-8 text-center shadow-sm">
          <p className="text-lg font-semibold text-gray-950">{error || "Menu not found"}</p>
          <p className="mt-2 text-sm text-gray-500">Please check the restaurant link or try again later.</p>
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
    <div className="min-h-screen bg-gray-50">
      <header className="sticky top-0 z-20 border-b border-gray-100 bg-white">
        <div className="mx-auto max-w-3xl px-4 py-4">
          <div className="flex items-center gap-3">
            {menuData.restaurant.logo_url && !logoFailed ? (
              <img
                src={menuData.restaurant.logo_url}
                alt={menuData.restaurant.name}
                referrerPolicy="no-referrer"
                onError={() => setLogoFailed(true)}
                className="h-14 w-14 rounded-lg border border-gray-100 object-cover"
              />
            ) : (
              <div className="flex h-14 w-14 items-center justify-center rounded-lg border border-orange-100 bg-orange-50 text-lg font-bold text-orange-700">
                {menuData.restaurant.name?.[0] || "R"}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <h1 className="truncate text-xl font-bold text-gray-950">{menuData.restaurant.name}</h1>
              <p className="mt-0.5 text-sm text-gray-500">{menuData.restaurant.city || "Menu"}</p>
              <p
                className={`mt-1 inline-flex rounded px-2 py-0.5 text-xs font-semibold ${
                  menuData.restaurant.is_open === false
                    ? "bg-red-50 text-red-700"
                    : "bg-green-50 text-green-700"
                }`}
              >
                {menuData.restaurant.is_open === false ? "Closed" : "Open now"}
              </p>
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

      {menuData.menu.length > 0 && (
        <div className="sticky top-[89px] z-10 overflow-x-auto border-b border-gray-100 bg-white">
          <div className="mx-auto flex max-w-3xl gap-2 px-4">
            {menuData.menu.map((category, idx) => (
              <button
                key={category.id}
                onClick={() => scrollToCategory(idx)}
                className={`whitespace-nowrap border-b-2 px-3 py-3 text-sm font-semibold transition-colors ${
                  activeCategory === idx
                    ? "border-orange-600 text-orange-700"
                    : "border-transparent text-gray-600 hover:text-gray-950"
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
          <div className="rounded-lg border border-gray-100 bg-white p-8 text-center shadow-sm">
            <p className="font-semibold text-gray-950">No items available right now</p>
            <p className="mt-2 text-sm text-gray-500">Please check back soon or ask the restaurant staff for today's specials.</p>
          </div>
        ) : (
          <div className="space-y-5 pb-10">
            {menuData.menu.map((category, idx) => (
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
