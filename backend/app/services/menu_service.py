import logging
import time
from collections import defaultdict
from threading import Event, Lock, Thread
from typing import Optional

from app.config.settings import settings
from app.services.supabase_service import supabase


logger = logging.getLogger(__name__)

PUBLIC_MENU_CACHE_TTL_SECONDS = settings.PUBLIC_MENU_CACHE_TTL_SECONDS
PUBLIC_MENU_STALE_SECONDS = settings.PUBLIC_MENU_STALE_SECONDS
PUBLIC_MENU_CACHE_MAX_SIZE = settings.PUBLIC_MENU_CACHE_MAX_SIZE
PUBLIC_MENU_SINGLEFLIGHT_WAIT_SECONDS = (
    settings.PUBLIC_MENU_SINGLEFLIGHT_WAIT_SECONDS
)

RESTAURANT_PUBLIC_COLUMNS = (
    "id,name,logo_url,city,is_active,is_open"
)

RESTAURANT_PUBLIC_FALLBACK_COLUMNS = (
    "id,name,logo_url,city,is_active"
)

CATEGORY_PUBLIC_COLUMNS = (
    "id,name,icon_emoji,display_order"
)

MENU_ITEM_PUBLIC_COLUMNS = (
    "id,category_id,name,description,price,mrp_price,image_url,"
    "is_available,is_veg,is_special,display_order"
)

_public_menu_cache = {}
_public_menu_refreshes = {}
_public_menu_cache_lock = Lock()
_public_menu_rpc_available = True


class RestaurantLookupError(RuntimeError):
    pass


class PublicMenuLoadError(RuntimeError):
    pass


class PublicMenuRpcUnavailable(RuntimeError):
    pass


def _is_not_found_error(exc: Exception):

    error_text = str(exc)

    return (
        "PGRST116" in error_text
        or "The result contains 0 rows" in error_text
        or "JSON object requested, multiple (or no) rows returned" in error_text
    )


def _is_missing_column_error(exc: Exception, column_name: str):

    error_text = str(exc)

    return (
        column_name in error_text
        and ("PGRST204" in error_text or "schema cache" in error_text)
    )


def _is_missing_rpc_error(exc: Exception):

    error_text = str(exc)

    return (
        "get_public_menu" in error_text
        and (
            "PGRST202" in error_text
            or "function" in error_text.lower()
            or "schema cache" in error_text
            or "does not exist" in error_text
        )
    )


def _cache_entry(slug: str):

    now = time.monotonic()

    cached = _public_menu_cache.get(slug)

    if not cached:
        return None

    expires_at, payload = cached
    stale_until = expires_at + PUBLIC_MENU_STALE_SECONDS

    if stale_until <= now:
        _public_menu_cache.pop(slug, None)
        return None

    return {
        "payload": payload,
        "is_fresh": expires_at > now,
        "is_stale": expires_at <= now < stale_until
    }


def _cache_get(slug: str, allow_stale: bool = False):

    with _public_menu_cache_lock:
        cached = _cache_entry(slug)

        if not cached:
            return None

        if cached["is_fresh"] or allow_stale:
            return cached["payload"]

        return None


def _cache_set(slug: str, payload):

    expires_at = time.monotonic() + PUBLIC_MENU_CACHE_TTL_SECONDS

    with _public_menu_cache_lock:
        if len(_public_menu_cache) >= PUBLIC_MENU_CACHE_MAX_SIZE:
            oldest_slug = next(iter(_public_menu_cache))
            _public_menu_cache.pop(oldest_slug, None)

        _public_menu_cache[slug] = (expires_at, payload)


def _begin_refresh(slug: str):

    with _public_menu_cache_lock:
        current_refresh = _public_menu_refreshes.get(slug)

        if current_refresh:
            return current_refresh, False

        refresh = Event()
        _public_menu_refreshes[slug] = refresh

        return refresh, True


def _finish_refresh(slug: str, refresh: Event):

    with _public_menu_cache_lock:
        if _public_menu_refreshes.get(slug) is refresh:
            _public_menu_refreshes.pop(slug, None)

        refresh.set()


def _refresh_public_menu_cache(slug: str, refresh: Event):

    try:
        response = _load_public_menu_by_slug_uncached(slug)

        if response and not response.get("inactive"):
            _cache_set(slug, response)
    except Exception as exc:
        logger.warning(
            "Background public menu refresh failed slug=%s error=%s",
            slug,
            exc
        )
    finally:
        _finish_refresh(slug, refresh)


def _refresh_public_menu_cache_in_background(slug: str):

    refresh, should_refresh = _begin_refresh(slug)

    if not should_refresh:
        return

    thread = Thread(
        target=_refresh_public_menu_cache,
        args=(slug, refresh),
        daemon=True
    )
    thread.start()


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
                .limit(1)
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

        return response.data[0] if response.data else None

    return None


def get_public_restaurant_by_slug(slug: str):

    try:
        response = (
            supabase.table("restaurants")
            .select(RESTAURANT_PUBLIC_COLUMNS)
            .eq("slug", slug)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        if _is_not_found_error(exc):
            return None

        if _is_missing_column_error(exc, "is_open"):
            logger.warning(
                "restaurants.is_open is missing; retrying public restaurant "
                "lookup without that optional column"
            )
            response = (
                supabase.table("restaurants")
                .select(RESTAURANT_PUBLIC_FALLBACK_COLUMNS)
                .eq("slug", slug)
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None

        logger.error(
            "Public restaurant lookup failed slug=%s error=%s",
            slug,
            exc,
            exc_info=True
        )
        raise RestaurantLookupError("Restaurant lookup failed") from exc

    return response.data[0] if response.data else None


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


def get_public_menu_via_rpc(slug: str):

    global _public_menu_rpc_available

    if not _public_menu_rpc_available:
        raise PublicMenuRpcUnavailable("Public menu RPC is unavailable")

    try:
        response = (
            supabase.rpc(
                "get_public_menu",
                {
                    "menu_slug": slug
                }
            )
            .execute()
        )
    except Exception as exc:
        if _is_missing_rpc_error(exc):
            _public_menu_rpc_available = False
            raise PublicMenuRpcUnavailable("Public menu RPC is unavailable") from exc

        logger.error(
            "Public menu RPC failed slug=%s error=%s",
            slug,
            exc,
            exc_info=True
        )
        raise

    return response.data


def _load_public_menu_by_slug_uncached(slug: str):

    try:
        rpc_response = get_public_menu_via_rpc(slug)

        if rpc_response is not None:
            return rpc_response
    except PublicMenuRpcUnavailable:
        logger.info(
            "Public menu RPC is not installed; falling back to REST queries"
        )

    restaurant = get_public_restaurant_by_slug(slug)

    if not restaurant:
        return None

    if not restaurant.get("is_active", True):
        return {
            "inactive": True,
            "restaurant": restaurant
        }

    categories = get_categories(
        restaurant["id"]
    )
    items = get_available_items(
        restaurant["id"]
    )

    return build_menu_response(
        restaurant,
        categories,
        items
    )


def get_public_menu_by_slug(slug: str):

    stale_payload = None

    with _public_menu_cache_lock:
        cached = _cache_entry(slug)

        if cached and cached["is_fresh"]:
            return cached["payload"]

        if cached and cached["is_stale"]:
            stale_payload = cached["payload"]

        active_refresh = _public_menu_refreshes.get(slug)

    if stale_payload is not None:
        _refresh_public_menu_cache_in_background(slug)
        return stale_payload

    if active_refresh:
        active_refresh.wait(PUBLIC_MENU_SINGLEFLIGHT_WAIT_SECONDS)

        with _public_menu_cache_lock:
            cached = _cache_entry(slug)

            if cached:
                return cached["payload"]

        raise PublicMenuLoadError("Public menu refresh timed out")

    try:
        refresh, should_refresh = _begin_refresh(slug)

        if not should_refresh:
            refresh.wait(PUBLIC_MENU_SINGLEFLIGHT_WAIT_SECONDS)

            with _public_menu_cache_lock:
                cached = _cache_entry(slug)

                if cached:
                    return cached["payload"]

            raise PublicMenuLoadError("Public menu refresh timed out")

        try:
            response = _load_public_menu_by_slug_uncached(slug)

            if response and not response.get("inactive"):
                _cache_set(slug, response)

            return response
        finally:
            _finish_refresh(slug, refresh)
    except RestaurantLookupError:
        raise
    except Exception as exc:
        stale_response = _cache_get(
            slug,
            allow_stale=True
        )

        if stale_response:
            logger.warning(
                "Serving stale public menu cache slug=%s error=%s",
                slug,
                exc
            )
            return stale_response

        logger.error(
            "Failed to load public menu slug=%s error=%s",
            slug,
            exc,
            exc_info=True
        )
        raise PublicMenuLoadError("Public menu load failed") from exc


def build_menu_response(
    restaurant,
    categories,
    items
):

    categorized_menu = []
    items_by_category = defaultdict(list)

    for item in items:
        items_by_category[item["category_id"]].append({
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

    for category in categories:

        category_items = items_by_category.get(
            category["id"],
            []
        )

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
