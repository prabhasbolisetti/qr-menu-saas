from app.services.supabase_service import supabase


def get_restaurant_by_slug(slug: str):

    response = (
        supabase.table("restaurants")
        .select("*")
        .eq("slug", slug)
        .single()
        .execute()
    )

    return response.data


def get_categories(restaurant_id: str):

    response = (
        supabase.table("categories")
        .select("*")
        .eq("restaurant_id", restaurant_id)
        .order("display_order")
        .execute()
    )

    return response.data


def get_available_items(restaurant_id: str):

    response = (
        supabase.table("menu_items")
        .select("*")
        .eq("restaurant_id", restaurant_id)
        .eq("is_available", True)
        .order("display_order")
        .execute()
    )

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
                    "is_veg": item["is_veg"],
                    "is_special": item["is_special"]
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
            "city": restaurant["city"]
        },
        "menu": categorized_menu
    }