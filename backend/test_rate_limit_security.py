import os
import unittest
from uuid import uuid4

from fastapi import HTTPException

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

from app.middleware.rate_limit import RateLimitPolicy, rate_limiter


class RateLimitSecurityTests(unittest.TestCase):

    def test_rate_limiter_rejects_requests_over_limit(self):

        policy = RateLimitPolicy(
            name="unit_test",
            limit=2,
            window_seconds=60
        )
        identifier = f"client-for-rate-limit-test-{uuid4()}"

        rate_limiter.check(policy, identifier)
        rate_limiter.check(policy, identifier)

        with self.assertRaises(HTTPException) as exc:
            rate_limiter.check(policy, identifier)

        self.assertEqual(exc.exception.status_code, 429)


if __name__ == "__main__":
    unittest.main()
