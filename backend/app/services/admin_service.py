from app.services.supabase_service import supabase


def create_restaurant(data):

    response = (
        supabase.table("restaurants")
        .insert({
            "owner_id": data.owner_id,
            "name": data.name,
            "slug": data.slug,
            "city": data.city,
            "logo_url": data.logo_url,
            "is_active": data.is_active
        })
        .execute()
    )

    return response.data[0]


def create_owner_account(data):

    response = supabase.auth.admin.create_user({
        "email": data.email,
        "password": data.password,
        "email_confirm": True,
        "user_metadata": {
            "role": "owner",
            "full_name": data.full_name
        },
        "app_metadata": {
            "role": "owner"
        }
    })

    user = response.user

    return {
        "id": user.id,
        "email": user.email,
        "role": "owner"
    }


def get_restaurant_by_id(restaurant_id: str):

    try:
        response = (
            supabase.table("restaurants")
            .select("*")
            .eq("id", restaurant_id)
            .single()
            .execute()
        )
    except Exception:
        return None

    return response.data




def create_category(data):

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


def get_categories(restaurant_id: str):

    response = (
        supabase.table("categories")
        .select("*")
        .eq("restaurant_id", restaurant_id)
        .order("display_order")
        .execute()
    )

    return response.data


def update_category(category_id: str, data):

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


def delete_category(category_id: str):

    response = (
        supabase.table("categories")
        .delete()
        .eq("id", category_id)
        .execute()
    )

    return response.data


def create_menu_item(data):

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


def update_menu_item(
    item_id: str,
    data
):

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


def delete_menu_item(item_id: str):

    response = (
        supabase.table("menu_items")
        .delete()
        .eq("id", item_id)
        .execute()
    )

    return response.data

def get_all_restaurants():

    response = (
        supabase.table("restaurants")
        .select("*")
        .order("created_at")
        .execute()
    )

    return response.data
