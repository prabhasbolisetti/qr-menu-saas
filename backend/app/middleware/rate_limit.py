from dataclasses import dataclass
from hashlib import sha256
from threading import Lock
import time

from fastapi import HTTPException, Request, status

from app.config.settings import settings


@dataclass(frozen=True)
class RateLimitPolicy:

    name: str
    limit: int
    window_seconds: int


LOGIN_POLICY = RateLimitPolicy(
    name="login",
    limit=5,
    window_seconds=60
)

PUBLIC_MENU_POLICY = RateLimitPolicy(
    name="public_menu",
    limit=120,
    window_seconds=60
)

OWNER_MUTATION_POLICY = RateLimitPolicy(
    name="owner_mutation",
    limit=60,
    window_seconds=60
)

UPLOAD_POLICY = RateLimitPolicy(
    name="upload",
    limit=20,
    window_seconds=3600
)


class InMemoryRateLimitStore:

    def __init__(self):

        self._lock = Lock()
        self._counters = {}

    def increment(self, key: str, window_seconds: int):

        now = time.time()

        with self._lock:
            count, expires_at = self._counters.get(
                key,
                (0, now + window_seconds)
            )

            if expires_at <= now:
                count = 0
                expires_at = now + window_seconds

            count += 1
            self._counters[key] = (count, expires_at)

            expired_keys = [
                stale_key
                for stale_key, (_, stale_expires_at) in self._counters.items()
                if stale_expires_at <= now
            ]

            for stale_key in expired_keys:
                self._counters.pop(stale_key, None)

        return count, max(1, int(expires_at - now))


class RedisRateLimitStore:

    def __init__(self, storage_url: str):

        try:
            import redis
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "The redis package is required when RATE_LIMIT_STORAGE_URL is set"
            ) from exc

        self._client = redis.Redis.from_url(
            storage_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2
        )

    def increment(self, key: str, window_seconds: int):

        count = self._client.incr(key)

        if count == 1:
            self._client.expire(
                key,
                window_seconds
            )

        ttl = self._client.ttl(key)

        if ttl < 0:
            self._client.expire(
                key,
                window_seconds
            )
            ttl = window_seconds

        return int(count), max(1, int(ttl))


class RateLimiter:

    def __init__(self):

        if settings.RATE_LIMIT_STORAGE_URL:
            self._store = RedisRateLimitStore(
                settings.RATE_LIMIT_STORAGE_URL
            )
        elif settings.is_production:
            raise RuntimeError(
                "RATE_LIMIT_STORAGE_URL must be configured in production"
            )
        else:
            self._store = InMemoryRateLimitStore()

    def check(self, policy: RateLimitPolicy, identifier: str):

        safe_identifier = sha256(
            identifier.encode("utf-8")
        ).hexdigest()
        window = int(time.time() // policy.window_seconds)
        key = f"qr-menu:{policy.name}:{safe_identifier}:{window}"
        count, retry_after = self._store.increment(
            key,
            policy.window_seconds
        )

        if count > policy.limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={
                    "Retry-After": str(retry_after)
                }
            )


rate_limiter = RateLimiter()


def client_ip(request: Request):

    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")

    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def check_login_rate_limit(request: Request):

    rate_limiter.check(
        LOGIN_POLICY,
        client_ip(request)
    )


def check_public_menu_rate_limit(request: Request):

    rate_limiter.check(
        PUBLIC_MENU_POLICY,
        client_ip(request)
    )


def check_owner_mutation_rate_limit(current_user):

    rate_limiter.check(
        OWNER_MUTATION_POLICY,
        current_user["user_id"]
    )


def check_upload_rate_limit(current_user):

    rate_limiter.check(
        UPLOAD_POLICY,
        current_user["user_id"]
    )
