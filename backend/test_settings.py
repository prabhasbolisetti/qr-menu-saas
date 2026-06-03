import os
import unittest
from unittest.mock import patch

from app.config.settings import Settings


PRODUCTION_ENV = {
    "ENVIRONMENT": "production",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_ANON_KEY": "test-anon-key",
    "SUPABASE_SERVICE_ROLE_KEY": "test-service-role-key",
    "FRONTEND_PUBLIC_BASE_URL": "https://frontend.example.com"
}


def build_settings(extra_env):

    with patch.dict(
        os.environ,
        {
            **PRODUCTION_ENV,
            **extra_env
        },
        clear=True
    ):
        return Settings()


class SettingsAllowedHostsTests(unittest.TestCase):

    def test_production_defaults_to_render_external_hostname(self):

        settings = build_settings({
            "RENDER_EXTERNAL_HOSTNAME": "qr-menu-api.onrender.com"
        })

        self.assertEqual(
            settings.allowed_hosts,
            ["qr-menu-api.onrender.com"]
        )
        settings.validate_backend_config()

    def test_blank_allowed_hosts_falls_back_to_render_external_url(self):

        settings = build_settings({
            "BACKEND_ALLOWED_HOSTS": " ",
            "RENDER_EXTERNAL_URL": "https://qr-menu-api.onrender.com"
        })

        self.assertEqual(
            settings.allowed_hosts,
            ["qr-menu-api.onrender.com"]
        )
        settings.validate_backend_config()

    def test_custom_allowed_hosts_keep_render_hostname_trusted(self):

        settings = build_settings({
            "BACKEND_ALLOWED_HOSTS": "https://api.example.com",
            "RENDER_EXTERNAL_HOSTNAME": "qr-menu-api.onrender.com"
        })

        self.assertEqual(
            settings.allowed_hosts,
            [
                "api.example.com",
                "qr-menu-api.onrender.com"
            ]
        )
        settings.validate_backend_config()

    def test_configured_wildcard_allowed_host_is_rejected_in_production(self):

        settings = build_settings({
            "BACKEND_ALLOWED_HOSTS": "*"
        })

        with self.assertRaisesRegex(
            RuntimeError,
            "BACKEND_ALLOWED_HOSTS cannot contain"
        ):
            settings.validate_backend_config()

    def test_missing_rate_limit_storage_warns_but_does_not_fail_startup(self):

        settings = build_settings({
            "RENDER_EXTERNAL_HOSTNAME": "qr-menu-api.onrender.com"
        })

        self.assertTrue(
            settings.rate_limit_storage_missing_in_production
        )
        settings.validate_backend_config()


if __name__ == "__main__":
    unittest.main()
