from app.services.supabase_service import supabase


def get_owner_restaurant(
    owner_id: str
):

    response = (
        supabase.table("restaurants")
        .select("*")
        .eq("owner_id", owner_id)
        .single()
        .execute()
    )

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