import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

from app.services import menu_service


class PublicMenuCacheTests(unittest.TestCase):

    def setUp(self):

        menu_service.clear_public_menu_cache()

    def test_cached_public_menu_reuses_payload_and_etag(self):

        load_count = 0
        payload = {
            "restaurant": {
                "id": "restaurant-1",
                "name": "Demo Cafe",
                "logo_url": None,
                "city": "Hyderabad",
                "is_open": True
            },
            "menu": [
                {
                    "id": "category-1",
                    "name": "Coffee",
                    "icon_emoji": None,
                    "items": [
                        {
                            "id": "item-1",
                            "name": "Filter Coffee",
                            "description": "Hot coffee",
                            "price": 80,
                            "mrp_price": 100,
                            "image_url": None,
                            "is_available": True,
                            "is_veg": True,
                            "is_special": False,
                            "is_bestseller": True
                        }
                    ]
                }
            ]
        }

        def load_menu(slug):

            nonlocal load_count
            load_count += 1
            self.assertEqual(slug, "demo-cafe")

            return payload

        with patch.object(
            menu_service,
            "_load_public_menu_by_slug_uncached",
            side_effect=load_menu
        ):
            first = menu_service.get_public_menu_metadata_by_slug("demo-cafe")
            second = menu_service.get_public_menu_metadata_by_slug("demo-cafe")

        self.assertEqual(load_count, 1)
        self.assertEqual(first["payload"], payload)
        self.assertEqual(second["payload"], payload)
        self.assertEqual(first["etag"], second["etag"])
        self.assertEqual(
            first["etag"],
            menu_service.build_public_menu_etag(payload)
        )


if __name__ == "__main__":
    unittest.main()
