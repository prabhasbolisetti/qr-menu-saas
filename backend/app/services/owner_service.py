from app.services.supabase_service import supabase


def get_owner_restaurant(
    owner_id: str
):

    try:
        response = (
            supabase.table("restaurants")
            .select("*")
            .eq("owner_id", owner_id)
            .single()
            .execute()
        )
    except Exception:
        return None

    return response.data


def get_owner_items(
    restaurant_id: str
):

    response = (
        supabase.table("menu_items")
        .select("*")
        .eq("restaurant_id", restaurant_id)
        .order("display_order")
        .execute()
    )

    return response.data


def get_owner_categories(
    restaurant_id: str
):

    response = (
        supabase.table("categories")
        .select("*")
        .eq("restaurant_id", restaurant_id)
        .order("display_order")
        .execute()
    )

    return response.data


def get_owner_item(
    restaurant_id: str,
    item_id: str
):

    try:
        response = (
            supabase.table("menu_items")
            .select("*")
            .eq("restaurant_id", restaurant_id)
            .eq("id", item_id)
            .single()
            .execute()
        )
    except Exception:
        return None

    return response.data


def get_owner_category(
    restaurant_id: str,
    category_id: str
):

    try:
        response = (
            supabase.table("categories")
            .select("*")
            .eq("restaurant_id", restaurant_id)
            .eq("id", category_id)
            .single()
            .execute()
        )
    except Exception:
        return None

    return response.data


def create_owner_category(data):

    response = (
        supabase.table("categories")
        .insert({
            "restaurant_id": data.restaurant_id,
            "name": data.name,
            "display_order": data.display_order,
            "icon_emoji": data.icon_emoji
        })
        .execute()
    )

    return response.data[0]


def update_owner_category(category_id: str, data):

    update_data = data.dict(
        exclude_unset=True
    )

    response = (
        supabase.table("categories")
        .update(update_data)
        .eq("id", category_id)
        .execute()
    )

    return response.data[0]


def delete_owner_category(category_id: str):

    response = (
        supabase.table("categories")
        .delete()
        .eq("id", category_id)
        .execute()
    )

    return response.data


def create_owner_item(data):

    response = (
        supabase.table("menu_items")
        .insert({
            "restaurant_id": data.restaurant_id,
            "category_id": data.category_id,
            "name": data.name,
            "description": data.description,
            "price": data.price,
            "mrp_price": data.mrp_price,
            "image_url": data.image_url,
            "is_available": data.is_available,
            "is_veg": data.is_veg,
            "is_special": data.is_special,
            "display_order": data.display_order
        })
        .execute()
    )

    return response.data[0]


def update_owner_item(item_id: str, data):

    update_data = data.dict(
        exclude_unset=True
    )

    response = (
        supabase.table("menu_items")
        .update(update_data)
        .eq("id", item_id)
        .execute()
    )

    return response.data[0]


def delete_owner_item(item_id: str):

    response = (
        supabase.table("menu_items")
        .delete()
        .eq("id", item_id)
        .execute()
    )

    return response.data


def toggle_item_availability(
    item_id: str,
    current_status: bool
):

    response = (
        supabase.table("menu_items")
        .update({
            "is_available": not current_status
        })
        .eq("id", item_id)
        .execute()
    )

    return response.data[0]


def update_item_price(
    item_id: str,
    price: float
):

    response = (
        supabase.table("menu_items")
        .update({
            "price": price
        })
        .eq("id", item_id)
        .execute()
    )

    return response.data[0]
