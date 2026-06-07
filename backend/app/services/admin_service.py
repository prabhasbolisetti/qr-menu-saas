from types import SimpleNamespace
import logging
from datetime import datetime, timezone

from app.services.audit_service import record_audit_event
from app.services.supabase_service import supabase
from app.services.menu_service import clear_public_menu_cache

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
                    "%s.deleted_at is missing; retrying admin %s without "
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

    def execute_update(next_payload: dict):

        if not next_payload:
            return _execute_with_optional_soft_delete_filter(
                "menu_items",
                "menu item select",
                lambda include_deleted_filter: _with_optional_soft_delete_filter(
                    supabase.table("menu_items")
                    .select("*")
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
                "menu_items.is_bestseller is missing in Supabase; retrying update "
                "without that optional column. Run backend/sql/production_readiness.sql "
                "to enable bestseller persistence."
            )

        response = execute_update(safe_payload)

    return response


def _execute_single_insert(table_name: str, payload: dict):

    try:
        logger.info(
            "Inserting row",
            extra={
                "fields": {
                    "table": table_name
                }
            }
        )
        response = (
            supabase.table(table_name)
            .insert(payload)
            .execute()
        )
        return _single_response_data(response, table_name)
    except Exception:
        logger.exception(
            "Insert failed",
            extra={
                "fields": {
                    "table": table_name
                }
            }
        )
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
        logger.exception(
            "Failed to sync owner database profile",
            extra={
                "fields": {
                    "user_id": user.id,
                    "email": user.email
                }
            }
        )
        raise


def create_restaurant(data, actor=None):

    payload = {
        "owner_id": data.owner_id,
        "name": data.name,
        "slug": data.slug,
        "city": data.city,
        "logo_url": data.logo_url,
        "is_active": data.is_active,
        "is_open": getattr(data, "is_open", True)
    }

    restaurant = _execute_single_insert(
        "restaurants",
        payload
    )

    record_audit_event(
        actor,
        "restaurant.created",
        "restaurant",
        restaurant.get("id"),
        restaurant.get("id"),
        {
            "name": restaurant.get("name"),
            "slug": restaurant.get("slug"),
            "owner_id": restaurant.get("owner_id")
        }
    )

    return restaurant


def create_owner_account(data):

    response = supabase.auth.admin.create_user({
        "email": data.email,
        "password": data.password,
        "email_confirm": True,
        "user_metadata": {
            "full_name": data.full_name
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


def onboard_restaurant(data, actor=None):

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
        ), actor=actor)
    except Exception:
        try:
            supabase.auth.admin.delete_user(owner["id"])
        except Exception:
            logger.exception(
                "Failed to rollback owner account after restaurant onboarding error",
                extra={
                    "fields": {
                        "owner_id": owner["id"]
                    }
                }
            )

        raise

    return {
        "owner": owner,
        "restaurant": restaurant
    }


def get_restaurant_by_id(restaurant_id: str):

    try:
        response = _execute_with_optional_soft_delete_filter(
            "restaurants",
            "restaurant lookup",
            lambda include_deleted_filter: _with_optional_soft_delete_filter(
                supabase.table("restaurants")
                .select("*")
                .eq("id", restaurant_id),
                include_deleted_filter
            ).single()
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
            "Failed to update restaurant open state restaurant_id=%s error=%s",
            restaurant_id,
            exc,
            exc_info=True
        )
        raise

    restaurant = _single_response_data(response, "restaurant")
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




def create_category(data, actor=None):

    try:
        payload = {
            "restaurant_id": data.restaurant_id,
            "name": data.name,
            "display_order": data.display_order,
            "icon_emoji": data.icon_emoji
        }
        logger.info(
            "Creating category",
            extra={
                "fields": {
                    "restaurant_id": data.restaurant_id
                }
            }
        )
        response = (
            supabase.table("categories")
            .insert(payload)
            .execute()
        )
        category = _single_response_data(response, "category after insert")
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
            "Failed to create category",
            extra={
                "fields": {
                    "restaurant_id": data.restaurant_id
                }
            }
        )
        raise


def get_categories(restaurant_id: str):

    try:
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
        response = _execute_with_optional_soft_delete_filter(
            "menu_items",
            "menu item lookup",
            lambda include_deleted_filter: _with_optional_soft_delete_filter(
                supabase.table("menu_items")
                .select("*")
                .eq("id", item_id),
                include_deleted_filter
            ).single()
        )
    except Exception as exc:
        logger.warning(
            "Menu item lookup failed item_id=%s error=%s",
            item_id,
            exc
        )
        return None

    return response.data


def get_menu_item_by_id_including_deleted(item_id: str):

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
            "Menu item lookup including deleted failed item_id=%s error=%s",
            item_id,
            exc
        )
        return None

    return response.data


def get_category_by_id_including_deleted(category_id: str):

    try:
        response = (
            supabase.table("categories")
            .select("*")
            .eq("id", category_id)
            .single()
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "Category lookup including deleted failed category_id=%s error=%s",
            category_id,
            exc
        )
        return None

    return response.data


def update_category(category_id: str, data, actor=None):

    update_data = _model_update_payload(data)

    response = _execute_with_optional_soft_delete_filter(
        "categories",
        "category update",
        lambda include_deleted_filter: _with_optional_soft_delete_filter(
            supabase.table("categories")
            .update(update_data)
            .eq("id", category_id),
            include_deleted_filter
        )
    )

    category = _single_response_data(response, "category after update")
    clear_public_menu_cache(category.get("restaurant_id"))
    record_audit_event(
        actor,
        "category.updated",
        "category",
        category.get("id"),
        category.get("restaurant_id"),
        update_data
    )
    return category


def delete_category(category_id: str, actor=None):

    response = (
        supabase.table("categories")
        .update(_soft_delete_payload(actor))
        .eq("id", category_id)
        .is_("deleted_at", "null")
        .execute()
    )

    for category in response.data or []:
        item_response = (
            supabase.table("menu_items")
            .update(_soft_delete_payload(actor))
            .eq("category_id", category_id)
            .is_("deleted_at", "null")
            .execute()
        )
        clear_public_menu_cache(category.get("restaurant_id"))
        record_audit_event(
            actor,
            "category.deleted",
            "category",
            category.get("id"),
            category.get("restaurant_id"),
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
                item.get("restaurant_id"),
                {
                    "name": item.get("name"),
                    "deleted_with_category_id": category_id
                }
            )

    return response.data


def restore_category(category_id: str, actor=None):

    response = (
        supabase.table("categories")
        .update(_restore_payload())
        .eq("id", category_id)
        .execute()
    )

    category = _single_response_data(response, "category after restore")
    clear_public_menu_cache(category.get("restaurant_id"))
    record_audit_event(
        actor,
        "category.restored",
        "category",
        category.get("id"),
        category.get("restaurant_id"),
        {
            "name": category.get("name")
        }
    )
    return category


def create_menu_item(data, actor=None):

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
        logger.info(
            "Creating menu item",
            extra={
                "fields": {
                    "restaurant_id": data.restaurant_id,
                    "category_id": data.category_id
                }
            }
        )
        response = _insert_menu_item_with_schema_fallback(payload)
        item = _single_response_data(response, "menu item after insert")
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
            "Failed to create menu item",
            extra={
                "fields": {
                    "restaurant_id": data.restaurant_id,
                    "category_id": data.category_id
                }
            }
        )
        raise


def update_menu_item(
    item_id: str,
    data,
    actor=None
):

    update_data = _model_update_payload(data)

    response = _update_menu_item_with_schema_fallback(
        item_id,
        update_data
    )

    item = _single_response_data(response, "menu item after update")
    clear_public_menu_cache(item.get("restaurant_id"))
    record_audit_event(
        actor,
        "item.updated",
        "menu_item",
        item.get("id"),
        item.get("restaurant_id"),
        update_data
    )
    return item


def delete_menu_item(item_id: str, actor=None):

    response = (
        supabase.table("menu_items")
        .update(_soft_delete_payload(actor))
        .eq("id", item_id)
        .is_("deleted_at", "null")
        .execute()
    )

    for item in response.data or []:
        clear_public_menu_cache(item.get("restaurant_id"))
        record_audit_event(
            actor,
            "item.deleted",
            "menu_item",
            item.get("id"),
            item.get("restaurant_id"),
            {
                "name": item.get("name")
            }
        )

    return response.data


def restore_menu_item(item_id: str, actor=None):

    response = (
        supabase.table("menu_items")
        .update(_restore_payload())
        .eq("id", item_id)
        .execute()
    )

    item = _single_response_data(response, "menu item after restore")
    clear_public_menu_cache(item.get("restaurant_id"))
    record_audit_event(
        actor,
        "item.restored",
        "menu_item",
        item.get("id"),
        item.get("restaurant_id"),
        {
            "name": item.get("name")
        }
    )
    return item

def get_all_restaurants():

    response = _execute_with_optional_soft_delete_filter(
        "restaurants",
        "restaurant list",
        lambda include_deleted_filter: _with_optional_soft_delete_filter(
            supabase.table("restaurants")
            .select("*"),
            include_deleted_filter
        ).order("created_at")
    )

    return response.data
