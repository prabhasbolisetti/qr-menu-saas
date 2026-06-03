import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

from app.config.settings import settings


request_id_var = contextvars.ContextVar(
    "request_id",
    default=None
)


def set_request_id(request_id: str):

    return request_id_var.set(request_id)


def reset_request_id(token):

    request_id_var.reset(token)


def get_request_id():

    return request_id_var.get()


class JsonLogFormatter(logging.Formatter):

    def format(self, record):

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id()
        }

        fields = getattr(record, "fields", None)

        if isinstance(fields, dict):
            payload.update(fields)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(
            payload,
            default=str,
            separators=(",", ":")
        )


def configure_logging():

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    if settings.LOG_FORMAT == "json":
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))

    root_logger.addHandler(handler)
