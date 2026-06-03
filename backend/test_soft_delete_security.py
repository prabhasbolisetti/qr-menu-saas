import inspect
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

from app.services import admin_service, menu_service, owner_service


class QueryRecorder:

    def __init__(self):

        self.calls = []

    def select(self, value):

        self.calls.append(("select", value))
        return self

    def eq(self, key, value):

        self.calls.append(("eq", key, value))
        return self

    def is_(self, key, value):

        self.calls.append(("is_", key, value))
        return self

    def order(self, value):

        self.calls.append(("order", value))
        return self

    def execute(self):

        return SimpleNamespace(data=[])


class FakeSupabase:

    def __init__(self, query):

        self.query = query

    def table(self, table_name):

        self.query.calls.append(("table", table_name))
        return self.query


class SoftDeleteSecurityTests(unittest.TestCase):

    def test_public_available_items_filters_deleted_rows(self):

        query = QueryRecorder()

        with patch.object(
            menu_service,
            "supabase",
            FakeSupabase(query)
        ):
            menu_service.get_available_items("restaurant-1")

        self.assertIn(
            ("is_", "deleted_at", "null"),
            query.calls
        )

    def test_service_delete_paths_do_not_call_hard_delete(self):

        for function in [
            owner_service.delete_owner_item,
            owner_service.delete_owner_category,
            admin_service.delete_menu_item,
            admin_service.delete_category
        ]:
            source = inspect.getsource(function)
            self.assertIn(".update(", source)
            self.assertNotIn(".delete(", source)


if __name__ == "__main__":
    unittest.main()
