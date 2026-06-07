from app.services.supabase_service import supabase
from app.services.menu_service import clear_public_menu_cache
from app.services.audit_service import record_audit_event
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _model_update_payload(data):

    if hasattr(data, "model_dump"):
        return data.model_dump(exclude_unset=True)

    return data.dict(exclude_unset=True)


def _single_response_data(response, resource_name: str):

    if not response.data:
        raise RuntimeError(f"Supabase returned no {resource_name}")

    return response.data[0]


def _utcnow_iso():

    return datetime.now(timezone.utc).isoformat()


def _soft_delete_payload(actor=None):

    payload = {
        "deleted_at": _utcnow_iso()
    }

    if actor:
        payload["deleted_by"] = actor.get("user_id")

    return payload


def _restore_payload():

    return {
        "deleted_at": None,
        "deleted_by": None
    }


def _is_missing_bestseller_column_error(exc: Exception):

    error_text = str(exc)
    normalized_error_text = error_text.lower()

    return (
        "is_bestseller" in error_text
        and "menu_items" in error_text
        and (
            "PGRST204" in error_text
            or "schema cache" in error_text
            or "42703" in error_text
            or "does not exist" in normalized_error_text
        )
    )


def _is_missing_column_error(exc: Exception, column_name: str):

    error_text = str(exc).lower()

    return (
        column_name.lower() in error_text
        and (
            "pgrst204" in error_text
            or "schema cache" in error_text
            or "42703" in error_text
            or "does not exist" in error_text
        )
    )


def _with_optional_soft_delete_filter(query, include_deleted_filter: bool):

    if include_deleted_filter:
        return query.is_("deleted_at", "null")

    return query


def _execute_with_optional_soft_delete_filter(
    table_name: str,
    operation: str,
    build_query
):

    include_deleted_filter = True

    while True:
        try:
            return build_query(include_deleted_filter).execute()
        except Exception as exc:
            if (
                include_deleted_filter
                and _is_missing_column_error(exc, "deleted_at")
            ):
                logger.warning(
                    "%s.deleted_at is missing; retrying owner %s without "
                    "soft-delete filter",
                    table_name,
                    operation
                )
                include_deleted_filter = False
                continue

            raise


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

    def execute_update(next_payload: dict):

        if not next_payload:
            return _execute_with_optional_soft_delete_filter(
                "menu_items",
                "menu item select",
                lambda include_deleted_filter: _with_optional_soft_delete_filter(
                    supabase.table("menu_items")
                    .select("*")
                    .eq("restaurant_id", restaurant_id)
                    .eq("id", item_id),
                    include_deleted_filter
                )
            )

        return _execute_with_optional_soft_delete_filter(
            "menu_items",
            "menu item update",
            lambda include_deleted_filter: _with_optional_soft_delete_filter(
                supabase.table("menu_items")
                .update(next_payload)
                .eq("restaurant_id", restaurant_id)
                .eq("id", item_id),
                include_deleted_filter
            )
        )

    try:
        response = execute_update(payload)
    except Exception as exc:
        if not _is_missing_bestseller_column_error(exc):
            raise

        safe_payload = _menu_item_payload_without_optional_columns(payload)

        if safe_payload:
            logger.warning(
                "menu_items.is_bestseller is missing in Supabase; retrying owner update "
                "without that optional column. Run backend/sql/production_readiness.sql "
                "to enable bestseller persistence."
            )

        response = execute_update(safe_payload)

    return response


def _payload_value(data, key: str):

    if isinstance(data, dict):
        return data.get(key)

    return getattr(data, key)


def get_owner_restaurant(
    owner_id: str
):

    try:
        response = _execute_with_optional_soft_delete_filter(
            "restaurants",
            "restaurant lookup",
            lambda include_deleted_filter: _with_optional_soft_delete_filter(
                supabase.table("restaurants")
                .select("*")
                .eq("owner_id", owner_id),
                include_deleted_filter
            ).single()
        )
    except Exception:
        return None

    return response.data


def get_owner_items(
    restaurant_id: str
):

    response = _execute_with_optional_soft_delete_filter(
        "menu_items",
        "menu item lookup",
        lambda include_deleted_filter: _with_optional_soft_delete_filter(
            supabase.table("menu_items")
            .select("*")
            .eq("restaurant_id", restaurant_id),
            include_deleted_filter
        ).order("display_order")
    )

    return response.data


def get_owner_categories(
    restaurant_id: str
):

    response = _execute_with_optional_soft_delete_filter(
        "categories",
        "category lookup",
        lambda include_deleted_filter: _with_optional_soft_delete_filter(
            supabase.table("categories")
            .select("*")
            .eq("restaurant_id", restaurant_id),
            include_deleted_filter
        ).order("display_order")
    )

    return response.data


def get_owner_item(
    restaurant_id: str,
    item_id: str
):

    try:
        response = _execute_with_optional_soft_delete_filter(
            "menu_items",
            "menu item lookup",
            lambda include_deleted_filter: _with_optional_soft_delete_filter(
                supabase.table("menu_items")
                .select("*")
                .eq("restaurant_id", restaurant_id)
                .eq("id", item_id),
                include_deleted_filter
            ).single()
        )
    except Exception:
        return None

    return response.data


def get_owner_category(
    restaurant_id: str,
    category_id: str
):

    try:
        response = _execute_with_optional_soft_delete_filter(
            "categories",
            "category lookup",
            lambda include_deleted_filter: _with_optional_soft_delete_filter(
                supabase.table("categories")
                .select("*")
                .eq("restaurant_id", restaurant_id)
                .eq("id", category_id),
                include_deleted_filter
            ).single()
        )
    except Exception:
        return None

    return response.data


def get_owner_item_including_deleted(
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


def get_owner_category_including_deleted(
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


def create_owner_category(data, actor=None):

    try:
        payload = {
            "restaurant_id": _payload_value(data, "restaurant_id"),
            "name": _payload_value(data, "name"),
            "display_order": _payload_value(data, "display_order"),
            "icon_emoji": _payload_value(data, "icon_emoji")
        }
        logger.info(
            "Creating owner category",
            extra={
                "fields": {
                    "restaurant_id": payload["restaurant_id"]
                }
            }
        )
        response = (
            supabase.table("categories")
            .insert(payload)
            .execute()
        )
        category = _single_response_data(response, "owner category after insert")
        clear_public_menu_cache(category["restaurant_id"])
        record_audit_event(
            actor,
            "category.created",
            "category",
            category.get("id"),
            category.get("restaurant_id"),
            {
                "name": category.get("name")
            }
        )
        return category
    except Exception:
        logger.exception(
            "Failed to create owner category",
            extra={
                "fields": {
                    "restaurant_id": _payload_value(data, "restaurant_id")
                }
            }
        )
        raise


def update_owner_restaurant_open_state(
    restaurant_id: str,
    is_open: bool,
    actor=None
):

    try:
        response = _execute_with_optional_soft_delete_filter(
            "restaurants",
            "restaurant open-state update",
            lambda include_deleted_filter: _with_optional_soft_delete_filter(
                supabase.table("restaurants")
                .update({
                    "is_open": is_open
                })
                .eq("id", restaurant_id),
                include_deleted_filter
            )
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
    record_audit_event(
        actor,
        "restaurant.settings_changed",
        "restaurant",
        restaurant_id,
        restaurant_id,
        {
            "field": "is_open",
            "value": is_open
        }
    )
    return restaurant


def update_owner_category(
    restaurant_id: str,
    category_id: str,
    data,
    actor=None
):

    update_data = _model_update_payload(data)

    response = _execute_with_optional_soft_delete_filter(
        "categories",
        "category update",
        lambda include_deleted_filter: _with_optional_soft_delete_filter(
            supabase.table("categories")
            .update(update_data)
            .eq("restaurant_id", restaurant_id)
            .eq("id", category_id),
            include_deleted_filter
        )
    )

    category = _single_response_data(response, "owner category after update")
    clear_public_menu_cache(restaurant_id)
    record_audit_event(
        actor,
        "category.updated",
        "category",
        category.get("id"),
        restaurant_id,
        update_data
    )
    return category


def delete_owner_category(
    restaurant_id: str,
    category_id: str,
    actor=None
):

    response = (
        supabase.table("categories")
        .update(_soft_delete_payload(actor))
        .eq("restaurant_id", restaurant_id)
        .eq("id", category_id)
        .is_("deleted_at", "null")
        .execute()
    )

    item_response = (
        supabase.table("menu_items")
        .update(_soft_delete_payload(actor))
        .eq("restaurant_id", restaurant_id)
        .eq("category_id", category_id)
        .is_("deleted_at", "null")
        .execute()
    )

    clear_public_menu_cache(restaurant_id)

    for category in response.data or []:
        record_audit_event(
            actor,
            "category.deleted",
            "category",
            category.get("id"),
            restaurant_id,
            {
                "name": category.get("name")
            }
        )

    for item in item_response.data or []:
        record_audit_event(
            actor,
            "item.deleted",
            "menu_item",
            item.get("id"),
            restaurant_id,
            {
                "name": item.get("name"),
                "deleted_with_category_id": category_id
            }
        )

    return response.data


def restore_owner_category(
    restaurant_id: str,
    category_id: str,
    actor=None
):

    response = (
        supabase.table("categories")
        .update(_restore_payload())
        .eq("restaurant_id", restaurant_id)
        .eq("id", category_id)
        .execute()
    )

    category = _single_response_data(response, "owner category after restore")
    clear_public_menu_cache(restaurant_id)
    record_audit_event(
        actor,
        "category.restored",
        "category",
        category.get("id"),
        restaurant_id,
        {
            "name": category.get("name")
        }
    )
    return category


def create_owner_item(data, actor=None):

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
        logger.info(
            "Creating owner menu item",
            extra={
                "fields": {
                    "restaurant_id": payload["restaurant_id"],
                    "category_id": payload["category_id"]
                }
            }
        )
        response = _insert_menu_item_with_schema_fallback(payload)
        item = _single_response_data(response, "owner menu item after insert")
        clear_public_menu_cache(item["restaurant_id"])
        record_audit_event(
            actor,
            "item.created",
            "menu_item",
            item.get("id"),
            item.get("restaurant_id"),
            {
                "name": item.get("name"),
                "category_id": item.get("category_id")
            }
        )
        return item
    except Exception:
        logger.exception(
            "Failed to create owner menu item",
            extra={
                "fields": {
                    "restaurant_id": _payload_value(data, "restaurant_id"),
                    "category_id": _payload_value(data, "category_id")
                }
            }
        )
        raise


def update_owner_item(
    restaurant_id: str,
    item_id: str,
    data,
    actor=None
):

    update_data = _model_update_payload(data)

    response = _update_menu_item_with_schema_fallback(
        restaurant_id,
        item_id,
        update_data
    )

    item = _single_response_data(response, "owner menu item after update")
    clear_public_menu_cache(restaurant_id)
    record_audit_event(
        actor,
        "item.updated",
        "menu_item",
        item.get("id"),
        restaurant_id,
        update_data
    )
    return item


def delete_owner_item(
    restaurant_id: str,
    item_id: str,
    actor=None
):

    response = (
        supabase.table("menu_items")
        .update(_soft_delete_payload(actor))
        .eq("restaurant_id", restaurant_id)
        .eq("id", item_id)
        .is_("deleted_at", "null")
        .execute()
    )

    clear_public_menu_cache(restaurant_id)

    for item in response.data or []:
        record_audit_event(
            actor,
            "item.deleted",
            "menu_item",
            item.get("id"),
            restaurant_id,
            {
                "name": item.get("name")
            }
        )

    return response.data


def restore_owner_item(
    restaurant_id: str,
    item_id: str,
    actor=None
):

    response = (
        supabase.table("menu_items")
        .update(_restore_payload())
        .eq("restaurant_id", restaurant_id)
        .eq("id", item_id)
        .execute()
    )

    item = _single_response_data(response, "owner menu item after restore")
    clear_public_menu_cache(restaurant_id)
    record_audit_event(
        actor,
        "item.restored",
        "menu_item",
        item.get("id"),
        restaurant_id,
        {
            "name": item.get("name")
        }
    )
    return item


def toggle_item_availability(
    restaurant_id: str,
    item_id: str,
    current_status: bool,
    actor=None
):

    response = _execute_with_optional_soft_delete_filter(
        "menu_items",
        "menu item availability update",
        lambda include_deleted_filter: _with_optional_soft_delete_filter(
            supabase.table("menu_items")
            .update({
                "is_available": not current_status
            })
            .eq("restaurant_id", restaurant_id)
            .eq("id", item_id),
            include_deleted_filter
        )
    )

    item = _single_response_data(response, "owner menu item after toggle")
    clear_public_menu_cache(restaurant_id)
    record_audit_event(
        actor,
        "item.updated",
        "menu_item",
        item.get("id"),
        restaurant_id,
        {
            "field": "is_available",
            "value": item.get("is_available")
        }
    )
    return item


def update_item_price(
    restaurant_id: str,
    item_id: str,
    price: float,
    actor=None
):

    response = _execute_with_optional_soft_delete_filter(
        "menu_items",
        "menu item price update",
        lambda include_deleted_filter: _with_optional_soft_delete_filter(
            supabase.table("menu_items")
            .update({
                "price": price
            })
            .eq("restaurant_id", restaurant_id)
            .eq("id", item_id),
            include_deleted_filter
        )
    )

    item = _single_response_data(response, "owner menu item after price update")
    clear_public_menu_cache(restaurant_id)
    record_audit_event(
        actor,
        "item.updated",
        "menu_item",
        item.get("id"),
        restaurant_id,
        {
            "field": "price",
            "value": price
        }
    )
    return item
