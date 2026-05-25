from types import SimpleNamespace
import logging

from app.services.supabase_service import supabase

logger = logging.getLogger(__name__)


def _model_update_payload(data):

    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)

    return data.dict(exclude_unset=True)


def _single_response_data(response, resource_name: str):

    if not response.data:
        raise RuntimeError(f"Supabase returned no {resource_name}")

    return response.data[0]


def _is_missing_bestseller_column_error(exc: Exception):

    error_text = str(exc)

    return (
        "is_bestseller" in error_text
        and "menu_items" in error_text
        and ("PGRST204" in error_text or "schema cache" in error_text)
    )


def _menu_item_payload_without_optional_columns(payload: dict):

    safe_payload = payload.copy()
    safe_payload.pop("is_bestseller", None)

    return safe_payload


def _insert_menu_item_with_schema_fallback(payload: dict):

    try:
        response = (
            supabase.table("menu_items")
            .insert(payload)
            .execute()
        )
    except Exception as exc:
        if not _is_missing_bestseller_column_error(exc):
            raise

        logger.warning(
            "menu_items.is_bestseller is missing in Supabase; retrying insert "
            "without that optional column. Run backend/sql/production_readiness.sql "
            "to enable bestseller persistence."
        )
        response = (
            supabase.table("menu_items")
            .insert(_menu_item_payload_without_optional_columns(payload))
            .execute()
        )

    return response


def _update_menu_item_with_schema_fallback(item_id: str, payload: dict):

    try:
        response = (
            supabase.table("menu_items")
            .update(payload)
            .eq("id", item_id)
            .execute()
        )
    except Exception as exc:
        if not _is_missing_bestseller_column_error(exc):
            raise

        safe_payload = _menu_item_payload_without_optional_columns(payload)

        if not safe_payload:
            response = (
                supabase.table("menu_items")
                .select("*")
                .eq("id", item_id)
                .execute()
            )
        else:
            logger.warning(
                "menu_items.is_bestseller is missing in Supabase; retrying update "
                "without that optional column. Run backend/sql/production_readiness.sql "
                "to enable bestseller persistence."
            )
            response = (
                supabase.table("menu_items")
                .update(safe_payload)
                .eq("id", item_id)
                .execute()
            )

    return response


def _execute_single_insert(table_name: str, payload: dict):

    try:
        logger.info(f"Inserting into {table_name}: {payload}")
        response = (
            supabase.table(table_name)
            .insert(payload)
            .execute()
        )
        logger.info(f"Insert successful: {response.data}")
        return _single_response_data(response, table_name)
    except Exception as e:
        logger.error(f"Insert failed for {table_name}: {str(e)}", exc_info=True)
        raise


def _sync_owner_profile(user, full_name: str | None = None):

    base_profile = {
        "id": user.id,
        "email": user.email,
        "role": "owner"
    }

    try:
        response = (
            supabase.table("profiles")
            .upsert({
                **base_profile,
                "full_name": full_name
            })
            .execute()
        )

        return response.data[0] if response.data else base_profile
    except Exception:
        try:
            response = (
                supabase.table("profiles")
                .upsert(base_profile)
                .execute()
            )

            return response.data[0] if response.data else base_profile
        except Exception:
            return base_profile


def create_restaurant(data):

    payload = {
        "owner_id": data.owner_id,
        "name": data.name,
        "slug": data.slug,
        "city": data.city,
        "logo_url": data.logo_url,
        "is_active": data.is_active,
        "is_open": getattr(data, "is_open", True)
    }

    return _execute_single_insert(
        "restaurants",
        payload
    )


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
    profile = _sync_owner_profile(
        user,
        data.full_name
    )

    return {
        "id": user.id,
        "email": user.email,
        "role": "owner",
        "profile": profile
    }


def onboard_restaurant(data):

    owner = create_owner_account(SimpleNamespace(
        email=data.owner_email,
        password=data.owner_password,
        full_name=data.owner_full_name
    ))

    try:
        restaurant = create_restaurant(SimpleNamespace(
            owner_id=owner["id"],
            name=data.name,
            slug=data.slug,
            city=data.city,
            logo_url=data.logo_url,
            is_active=data.is_active,
            is_open=data.is_open
        ))
    except Exception:
        try:
            supabase.auth.admin.delete_user(owner["id"])
        except Exception:
            pass

        raise

    return {
        "owner": owner,
        "restaurant": restaurant
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
    except Exception as exc:
        logger.warning(
            "Restaurant lookup failed restaurant_id=%s error=%s",
            restaurant_id,
            exc
        )
        return None

    return response.data


def update_restaurant_open_state(
    restaurant_id: str,
    is_open: bool
):

    try:
        response = (
            supabase.table("restaurants")
            .update({
                "is_open": is_open
            })
            .eq("id", restaurant_id)
            .execute()
        )
    except Exception as exc:
        logger.error(
            "Failed to update restaurant open state restaurant_id=%s error=%s",
            restaurant_id,
            exc,
            exc_info=True
        )
        raise

    return _single_response_data(response, "restaurant")




def create_category(data):

    try:
        payload = {
            "restaurant_id": data.restaurant_id,
            "name": data.name,
            "display_order": data.display_order,
            "icon_emoji": data.icon_emoji
        }
        logger.info(f"Creating category with payload: {payload}")
        response = (
            supabase.table("categories")
            .insert(payload)
            .execute()
        )
        logger.info(f"Category created: {response.data}")
        return _single_response_data(response, "category after insert")
    except Exception as e:
        logger.error(f"Failed to create category: {str(e)}", exc_info=True)
        raise


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
            "Failed to fetch categories restaurant_id=%s error=%s",
            restaurant_id,
            exc,
            exc_info=True
        )
        raise

    return response.data


def get_category_for_restaurant(
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
    except Exception as exc:
        logger.warning(
            "Category lookup failed restaurant_id=%s category_id=%s error=%s",
            restaurant_id,
            category_id,
            exc
        )
        return None

    return response.data


def get_menu_item_by_id(item_id: str):

    try:
        response = (
            supabase.table("menu_items")
            .select("*")
            .eq("id", item_id)
            .single()
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "Menu item lookup failed item_id=%s error=%s",
            item_id,
            exc
        )
        return None

    return response.data


def update_category(category_id: str, data):

    update_data = _model_update_payload(data)

    response = (
        supabase.table("categories")
        .update(update_data)
        .eq("id", category_id)
        .execute()
    )

    return _single_response_data(response, "category after update")


def delete_category(category_id: str):

    response = (
        supabase.table("categories")
        .delete()
        .eq("id", category_id)
        .execute()
    )

    return response.data


def create_menu_item(data):

    try:
        payload = {
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
            "is_bestseller": data.is_bestseller,
            "display_order": data.display_order
        }
        logger.info(f"Creating menu item with payload: {payload}")
        response = _insert_menu_item_with_schema_fallback(payload)
        logger.info(f"Menu item created: {response.data}")
        return _single_response_data(response, "menu item after insert")
    except Exception as e:
        logger.error(f"Failed to create menu item: {str(e)}", exc_info=True)
        raise


def update_menu_item(
    item_id: str,
    data
):

    update_data = _model_update_payload(data)

    response = _update_menu_item_with_schema_fallback(
        item_id,
        update_data
    )

    return _single_response_data(response, "menu item after update")


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
