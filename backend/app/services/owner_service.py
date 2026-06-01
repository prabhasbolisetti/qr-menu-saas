from app.services.supabase_service import supabase
from app.services.menu_service import clear_public_menu_cache
import logging

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
            "menu_items.is_bestseller is missing in Supabase; retrying owner insert "
            "without that optional column. Run backend/sql/production_readiness.sql "
            "to enable bestseller persistence."
        )
        response = (
            supabase.table("menu_items")
            .insert(_menu_item_payload_without_optional_columns(payload))
            .execute()
        )

    return response


def _update_menu_item_with_schema_fallback(
    restaurant_id: str,
    item_id: str,
    payload: dict
):

    try:
        response = (
            supabase.table("menu_items")
            .update(payload)
            .eq("restaurant_id", restaurant_id)
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
                .eq("restaurant_id", restaurant_id)
                .eq("id", item_id)
                .execute()
            )
        else:
            logger.warning(
                "menu_items.is_bestseller is missing in Supabase; retrying owner update "
                "without that optional column. Run backend/sql/production_readiness.sql "
                "to enable bestseller persistence."
            )
            response = (
                supabase.table("menu_items")
                .update(safe_payload)
                .eq("restaurant_id", restaurant_id)
                .eq("id", item_id)
                .execute()
            )

    return response


def _payload_value(data, key: str):

    if isinstance(data, dict):
        return data.get(key)

    return getattr(data, key)


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

    try:
        payload = {
            "restaurant_id": _payload_value(data, "restaurant_id"),
            "name": _payload_value(data, "name"),
            "display_order": _payload_value(data, "display_order"),
            "icon_emoji": _payload_value(data, "icon_emoji")
        }
        logger.info(f"Creating owner category with payload: {payload}")
        response = (
            supabase.table("categories")
            .insert(payload)
            .execute()
        )
        logger.info(f"Owner category created: {response.data}")
        category = _single_response_data(response, "owner category after insert")
        clear_public_menu_cache(category["restaurant_id"])
        return category
    except Exception as e:
        logger.error(f"Failed to create owner category: {str(e)}", exc_info=True)
        raise


def update_owner_restaurant_open_state(
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
            "Failed to update owner restaurant open state restaurant_id=%s error=%s",
            restaurant_id,
            exc,
            exc_info=True
        )
        raise

    restaurant = _single_response_data(response, "owner restaurant")
    clear_public_menu_cache(restaurant_id)
    return restaurant


def update_owner_category(
    restaurant_id: str,
    category_id: str,
    data
):

    update_data = _model_update_payload(data)

    response = (
        supabase.table("categories")
        .update(update_data)
        .eq("restaurant_id", restaurant_id)
        .eq("id", category_id)
        .execute()
    )

    category = _single_response_data(response, "owner category after update")
    clear_public_menu_cache(restaurant_id)
    return category


def delete_owner_category(
    restaurant_id: str,
    category_id: str
):

    response = (
        supabase.table("categories")
        .delete()
        .eq("restaurant_id", restaurant_id)
        .eq("id", category_id)
        .execute()
    )

    clear_public_menu_cache(restaurant_id)

    return response.data


def create_owner_item(data):

    try:
        payload = {
            "restaurant_id": _payload_value(data, "restaurant_id"),
            "category_id": _payload_value(data, "category_id"),
            "name": _payload_value(data, "name"),
            "description": _payload_value(data, "description"),
            "price": _payload_value(data, "price"),
            "mrp_price": _payload_value(data, "mrp_price"),
            "image_url": _payload_value(data, "image_url"),
            "is_available": _payload_value(data, "is_available"),
            "is_veg": _payload_value(data, "is_veg"),
            "is_special": _payload_value(data, "is_special"),
            "is_bestseller": _payload_value(data, "is_bestseller"),
            "display_order": _payload_value(data, "display_order")
        }
        logger.info(f"Creating owner menu item with payload: {payload}")
        response = _insert_menu_item_with_schema_fallback(payload)
        logger.info(f"Owner menu item created: {response.data}")
        item = _single_response_data(response, "owner menu item after insert")
        clear_public_menu_cache(item["restaurant_id"])
        return item
    except Exception as e:
        logger.error(f"Failed to create owner menu item: {str(e)}", exc_info=True)
        raise


def update_owner_item(
    restaurant_id: str,
    item_id: str,
    data
):

    update_data = _model_update_payload(data)

    response = _update_menu_item_with_schema_fallback(
        restaurant_id,
        item_id,
        update_data
    )

    item = _single_response_data(response, "owner menu item after update")
    clear_public_menu_cache(restaurant_id)
    return item


def delete_owner_item(
    restaurant_id: str,
    item_id: str
):

    response = (
        supabase.table("menu_items")
        .delete()
        .eq("restaurant_id", restaurant_id)
        .eq("id", item_id)
        .execute()
    )

    clear_public_menu_cache(restaurant_id)

    return response.data


def toggle_item_availability(
    restaurant_id: str,
    item_id: str,
    current_status: bool
):

    response = (
        supabase.table("menu_items")
        .update({
            "is_available": not current_status
        })
        .eq("restaurant_id", restaurant_id)
        .eq("id", item_id)
        .execute()
    )

    item = _single_response_data(response, "owner menu item after toggle")
    clear_public_menu_cache(restaurant_id)
    return item


def update_item_price(
    restaurant_id: str,
    item_id: str,
    price: float
):

    response = (
        supabase.table("menu_items")
        .update({
            "price": price
        })
        .eq("restaurant_id", restaurant_id)
        .eq("id", item_id)
        .execute()
    )

    item = _single_response_data(response, "owner menu item after price update")
    clear_public_menu_cache(restaurant_id)
    return item
