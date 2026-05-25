import logging

from app.services.supabase_service import supabase


logger = logging.getLogger(__name__)


def get_restaurant_by_slug(slug: str):

    try:
        response = (
            supabase.table("restaurants")
            .select("*")
            .eq("slug", slug)
            .single()
            .execute()
        )
    except Exception:
        return None

    return response.data


def get_categories(restaurant_id: str):

    try:
        response = (
            supabase.table("categories")
            .select("*")
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
            .select("*")
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
