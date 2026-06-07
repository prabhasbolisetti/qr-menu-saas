import os
import unittest

os.environ.setdefault("FRONTEND_PUBLIC_BASE_URL", "https://menus.example.com")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

from app.services.qr_service import (
    build_public_menu_url,
    build_qr_response
)


class QRServiceTests(unittest.TestCase):

    def test_qr_response_uses_first_party_data_url(self):

        response = build_qr_response({
            "id": "restaurant-1",
            "slug": "demo-cafe"
        }, base_url="https://menus.example.com")

        self.assertEqual(
            response["menu_url"],
            "https://menus.example.com/menu/demo-cafe"
        )
        self.assertTrue(
            response["qr_image_url"].startswith("data:image/png;base64,")
        )
        self.assertEqual(
            response["qr_image_url"],
            response["qr_image_data_url"]
        )

    def test_public_menu_url_encodes_slug(self):

        self.assertEqual(
            build_public_menu_url("demo cafe", base_url="https://menus.example.com/"),
            "https://menus.example.com/menu/demo%20cafe"
        )


if __name__ == "__main__":
    unittest.main()
