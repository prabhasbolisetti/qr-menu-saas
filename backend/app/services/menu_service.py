import logging
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Optional

from app.services.supabase_service import supabase


logger = logging.getLogger(__name__)

PUBLIC_MENU_CACHE_TTL_SECONDS = 120
PUBLIC_MENU_CACHE_MAX_SIZE = 256

RESTAURANT_PUBLIC_COLUMNS = (
    "id,name,logo_url,city,is_active,is_open"
)

CATEGORY_PUBLIC_COLUMNS = (
    "id,name,icon_emoji,display_order"
)

MENU_ITEM_PUBLIC_COLUMNS = (
    "id,category_id,name,description,price,mrp_price,image_url,"
    "is_available,is_veg,is_special,is_bestseller,display_order"
)

_public_menu_cache = {}
_public_menu_cache_lock = Lock()


class RestaurantLookupError(RuntimeError):
    pass


def _is_not_found_error(exc: Exception):

    error_text = str(exc)

    return (
        "PGRST116" in error_text
        or "The result contains 0 rows" in error_text
        or "JSON object requested, multiple (or no) rows returned" in error_text
    )


def _cache_get(slug: str):

    now = time.monotonic()

    with _public_menu_cache_lock:
        cached = _public_menu_cache.get(slug)

        if not cached:
            return None

        expires_at, payload = cached

        if expires_at <= now:
            _public_menu_cache.pop(slug, None)
            return None

        return payload


def _cache_set(slug: str, payload):

    expires_at = time.monotonic() + PUBLIC_MENU_CACHE_TTL_SECONDS

    with _public_menu_cache_lock:
        if len(_public_menu_cache) >= PUBLIC_MENU_CACHE_MAX_SIZE:
            oldest_slug = next(iter(_public_menu_cache))
            _public_menu_cache.pop(oldest_slug, None)

        _public_menu_cache[slug] = (expires_at, payload)


def clear_public_menu_cache(restaurant_id: Optional[str] = None):

    with _public_menu_cache_lock:
        if restaurant_id is None:
            _public_menu_cache.clear()
            return

        stale_slugs = [
            slug
            for slug, (_, payload) in _public_menu_cache.items()
            if payload.get("restaurant", {}).get("id") == restaurant_id
        ]

        for slug in stale_slugs:
            _public_menu_cache.pop(slug, None)


def get_restaurant_by_slug(slug: str):

    for attempt in range(2):
        try:
            response = (
                supabase.table("restaurants")
                .select("*")
                .eq("slug", slug)
                .single()
                .execute()
            )
        except Exception as exc:
            if _is_not_found_error(exc):
                return None

            if attempt == 0:
                logger.warning(
                    "Restaurant lookup failed, retrying slug=%s error=%s",
                    slug,
                    exc
                )
                time.sleep(0.2)
                continue

            logger.error(
                "Restaurant lookup failed slug=%s error=%s",
                slug,
                exc,
                exc_info=True
            )
            raise RestaurantLookupError("Restaurant lookup failed") from exc

        return response.data

    return None


def get_public_restaurant_by_slug(slug: str):

    try:
        response = (
            supabase.table("restaurants")
            .select(RESTAURANT_PUBLIC_COLUMNS)
            .eq("slug", slug)
            .single()
            .execute()
        )
    except Exception as exc:
        if _is_not_found_error(exc):
            return None

        logger.error(
            "Public restaurant lookup failed slug=%s error=%s",
            slug,
            exc,
            exc_info=True
        )
        raise RestaurantLookupError("Restaurant lookup failed") from exc

    return response.data


def get_categories(restaurant_id: str):

    try:
        response = (
            supabase.table("categories")
            .select(CATEGORY_PUBLIC_COLUMNS)
            .eq("restaurant_id", restaurant_id)
            .order("display_order")
            .execute()
        )
    except Exception as exc:
        logger.error(
            "Failed to fetch menu categories restaurant_id=%s error=%s",
            restaurant_id,
            exc,
            exc_info=True
        )
        raise

    return response.data


def get_available_items(restaurant_id: str):

    try:
        response = (
            supabase.table("menu_items")
            .select(MENU_ITEM_PUBLIC_COLUMNS)
            .eq("restaurant_id", restaurant_id)
            .eq("is_available", True)
            .order("display_order")
            .execute()
        )
    except Exception as exc:
        logger.error(
            "Failed to fetch available menu items restaurant_id=%s error=%s",
            restaurant_id,
            exc,
            exc_info=True
        )
        raise

    return response.data


def get_all_items(restaurant_id: str):

    try:
        response = (
            supabase.table("menu_items")
            .select("*")
            .eq("restaurant_id", restaurant_id)
            .order("display_order")
            .execute()
        )
    except Exception as exc:
        logger.error(
            "Failed to fetch menu items restaurant_id=%s error=%s",
            restaurant_id,
            exc,
            exc_info=True
        )
        raise

    return response.data


def get_public_menu_by_slug(slug: str):

    cached = _cache_get(slug)

    if cached:
        return cached

    restaurant = get_public_restaurant_by_slug(slug)

    if not restaurant:
        return None

    if not restaurant["is_active"]:
        return {
            "inactive": True,
            "restaurant": restaurant
        }

    with ThreadPoolExecutor(max_workers=2) as executor:
        categories_future = executor.submit(
            get_categories,
            restaurant["id"]
        )
        items_future = executor.submit(
            get_available_items,
            restaurant["id"]
        )

        categories = categories_future.result()
        items = items_future.result()

    response = build_menu_response(
        restaurant,
        categories,
        items
    )

    _cache_set(slug, response)

    return response


def build_menu_response(
    restaurant,
    categories,
    items
):

    categorized_menu = []

    for category in categories:

        category_items = []

        for item in items:

            if item["category_id"] == category["id"]:

                category_items.append({
                    "id": item["id"],
                    "name": item["name"],
                    "description": item["description"],
                    "price": item["price"],
                    "mrp_price": item["mrp_price"],
                    "image_url": item["image_url"],
                    "is_available": item.get("is_available", True),
                    "is_veg": item.get("is_veg", False),
                    "is_special": item.get("is_special", False),
                    "is_bestseller": item.get(
                        "is_bestseller",
                        item.get("is_special", False)
                    )
                })

        if category_items:

            categorized_menu.append({
                "id": category["id"],
                "name": category["name"],
                "icon_emoji": category["icon_emoji"],
                "items": category_items
            })

    return {
        "restaurant": {
            "id": restaurant["id"],
            "name": restaurant["name"],
            "logo_url": restaurant["logo_url"],
            "city": restaurant["city"],
            "is_open": restaurant.get("is_open", True)
        },
        "menu": categorized_menu
    }
