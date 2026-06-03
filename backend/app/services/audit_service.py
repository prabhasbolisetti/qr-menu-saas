import logging

from app.services.supabase_service import supabase


logger = logging.getLogger(__name__)


def record_audit_event(
    actor,
    action: str,
    entity_type: str,
    entity_id: str | None,
    restaurant_id: str | None,
    entity: dict | None = None
):

    if not actor:
        return

    payload = {
        "actor_id": actor.get("user_id"),
        "actor_role": actor.get("role"),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "restaurant_id": restaurant_id,
        "entity": entity or {}
    }

    try:
        supabase.table("audit_logs").insert(payload).execute()
    except Exception:
        logger.exception(
            "Failed to record audit event",
            extra={
                "fields": {
                    "action": action,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "restaurant_id": restaurant_id,
                    "actor_id": payload["actor_id"]
                }
            }
        )
