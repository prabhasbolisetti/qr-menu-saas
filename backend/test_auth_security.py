import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

from app.middleware.auth_middleware import build_user_identity


class AuthSecurityTests(unittest.TestCase):

    def test_database_role_overrides_metadata_role(self):

        user = SimpleNamespace(
            id="user-1",
            email="owner@example.com",
            user_metadata={"role": "super"},
            app_metadata={"role": "super"}
        )

        with patch(
            "app.middleware.auth_middleware._get_profile",
            return_value={
                "id": "user-1",
                "email": "owner@example.com",
                "role": "owner"
            }
        ):
            identity = build_user_identity(user)

        self.assertEqual(identity["role"], "owner")

    def test_metadata_role_without_database_profile_is_rejected(self):

        user = SimpleNamespace(
            id="user-2",
            email="attacker@example.com",
            user_metadata={"role": "super"},
            app_metadata={"role": "super"}
        )

        with patch(
            "app.middleware.auth_middleware._get_profile",
            return_value=None
        ):
            with self.assertRaises(HTTPException) as exc:
                build_user_identity(user)

        self.assertEqual(exc.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
