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