#!/usr/bin/env python3
"""
Seed realistic Burger Empire demo data.

Run after backend/sql/production_readiness.sql has been applied.
The script creates/updates Supabase Auth users through the Admin API,
syncs profiles, links the owner to Burger Empire, and replaces only
the Burger Empire demo categories/items.
"""

import os
import sys
from urllib import request, parse
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

SUPER_EMAIL = os.getenv("SEED_SUPER_EMAIL", "super@burgerempire.demo")
SUPER_PASSWORD = os.getenv("SEED_SUPER_PASSWORD", "SuperAdmin123!")
OWNER_EMAIL = os.getenv("SEED_OWNER_EMAIL", "owner@burgerempire.demo")
OWNER_PASSWORD = os.getenv("SEED_OWNER_PASSWORD", "OwnerPass123!")

RESTAURANT = {
    "name": "Burger Empire",
    "slug": "burger-empire",
    "city": "Hyderabad",
    "logo_url": "https://images.unsplash.com/photo-1571091718767-18b5b1457add?auto=format&fit=crop&w=400&q=80",
    "is_active": True,
    "is_open": True,
}

CATEGORIES = [
    {"name": "Burgers", "display_order": 1, "icon_emoji": "burger"},
    {"name": "Starters", "display_order": 2, "icon_emoji": "fries"},
    {"name": "Cool Drinks", "display_order": 3, "icon_emoji": "drink"},
    {"name": "Desserts", "display_order": 4, "icon_emoji": "dessert"},
]

ITEMS = [
    {
        "category": "Burgers",
        "name": "Smoky Chicken Burger",
        "description": "Grilled chicken patty, smoked sauce, lettuce, onions, and cheese in a toasted bun.",
        "price": 249,
        "mrp_price": 299,
        "image_url": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=800&q=80",
        "is_available": True,
        "is_veg": False,
        "is_special": True,
        "is_bestseller": True,
        "display_order": 1,
    },
    {
        "category": "Burgers",
        "name": "Crispy Veg Burger",
        "description": "Crispy vegetable patty, fresh tomato, lettuce, and house mayo.",
        "price": 179,
        "mrp_price": 219,
        "image_url": "https://images.unsplash.com/photo-1520072959219-c595dc870360?auto=format&fit=crop&w=800&q=80",
        "is_available": True,
        "is_veg": True,
        "is_special": False,
        "is_bestseller": True,
        "display_order": 2,
    },
    {
        "category": "Starters",
        "name": "French Fries",
        "description": "Golden fries tossed with peri-peri seasoning and served with dip.",
        "price": 119,
        "mrp_price": None,
        "image_url": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&w=800&q=80",
        "is_available": True,
        "is_veg": True,
        "is_special": False,
        "is_bestseller": False,
        "display_order": 1,
    },
    {
        "category": "Cool Drinks",
        "name": "Coke",
        "description": "Chilled 330 ml can.",
        "price": 60,
        "mrp_price": None,
        "image_url": "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?auto=format&fit=crop&w=800&q=80",
        "is_available": True,
        "is_veg": True,
        "is_special": False,
        "is_bestseller": False,
        "display_order": 1,
    },
    {
        "category": "Desserts",
        "name": "Brownie",
        "description": "Dense chocolate brownie with a soft center.",
        "price": 139,
        "mrp_price": 159,
        "image_url": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=800&q=80",
        "is_available": False,
        "is_veg": True,
        "is_special": True,
        "is_bestseller": False,
        "display_order": 1,
    },
]


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


def require_env():
    missing = [
        key
        for key, value in {
            "SUPABASE_URL": SUPABASE_URL,
            "SUPABASE_SERVICE_ROLE_KEY": SERVICE_ROLE_KEY,
        }.items()
        if not value
    ]

    if missing:
        print(f"Missing required env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)


def auth_admin_request(method, path, payload=None):
    url = f"{SUPABASE_URL}/auth/v1{path}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        method=method,
        headers={
            "apikey": SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
        },
    )

    with request.urlopen(req, timeout=30) as response:
        text = response.read().decode("utf-8")
        return json.loads(text) if text else {}


def find_auth_user(email):
    page = 1

    while True:
        query = parse.urlencode({"page": page, "per_page": 200})
        payload = auth_admin_request("GET", f"/admin/users?{query}")
        users = payload.get("users", [])

        for user in users:
            if user.get("email", "").lower() == email.lower():
                return user

        if len(users) < 200:
            return None

        page += 1


def upsert_auth_user(email, password, role, full_name):
    existing = find_auth_user(email)
    payload = {
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {
            "full_name": full_name,
        },
    }

    if existing:
        user_id = existing["id"]
        auth_admin_request("PUT", f"/admin/users/{user_id}", payload)
        return {**existing, **payload, "id": user_id}

    return auth_admin_request("POST", "/admin/users", payload)


def main():
    require_env()
    supabase = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

    try:
        supabase.table("menu_items").select("is_bestseller").limit(1).execute()
    except Exception as exc:
        print(
            "Schema migration required before seeding: "
            "menu_items.is_bestseller is missing. "
            "Apply backend/sql/production_readiness.sql first.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    super_user = upsert_auth_user(
        SUPER_EMAIL,
        SUPER_PASSWORD,
        "super",
        "Platform Super Admin",
    )
    owner_user = upsert_auth_user(
        OWNER_EMAIL,
        OWNER_PASSWORD,
        "owner",
        "Burger Empire Owner",
    )

    for user, role, full_name in [
        (super_user, "super", "Platform Super Admin"),
        (owner_user, "owner", "Burger Empire Owner"),
    ]:
        supabase.table("profiles").upsert({
            "id": user["id"],
            "email": user["email"],
            "role": role,
            "full_name": full_name,
        }).execute()

    restaurant_payload = {
        **RESTAURANT,
        "owner_id": owner_user["id"],
        "deleted_at": None,
        "deleted_by": None,
    }

    existing_restaurants = (
        supabase.table("restaurants")
        .select("*")
        .eq("slug", RESTAURANT["slug"])
        .limit(1)
        .execute()
        .data
    )

    if existing_restaurants:
        restaurant_id = existing_restaurants[0]["id"]
        restaurant_response = (
            supabase.table("restaurants")
            .update(restaurant_payload)
            .eq("id", restaurant_id)
            .execute()
        )
    else:
        restaurant_response = (
            supabase.table("restaurants")
            .insert(restaurant_payload)
            .execute()
        )

    restaurant = restaurant_response.data[0]

    existing_categories = (
        supabase.table("categories")
        .select("id")
        .eq("restaurant_id", restaurant["id"])
        .is_("deleted_at", "null")
        .execute()
        .data
    )
    for category in existing_categories:
        deleted_at = utcnow_iso()
        (
            supabase.table("categories")
            .update({"deleted_at": deleted_at})
            .eq("id", category["id"])
            .execute()
        )
        (
            supabase.table("menu_items")
            .update({"deleted_at": deleted_at})
            .eq("category_id", category["id"])
            .is_("deleted_at", "null")
            .execute()
        )

    category_ids = {}
    for category in CATEGORIES:
        payload = {**category, "restaurant_id": restaurant["id"]}
        response = supabase.table("categories").insert(payload).execute()
        category_ids[category["name"]] = response.data[0]["id"]

    for item in ITEMS:
        item_payload = item.copy()
        category_name = item_payload.pop("category")
        payload = {
            **item_payload,
            "restaurant_id": restaurant["id"],
            "category_id": category_ids[category_name],
        }
        supabase.table("menu_items").insert(payload).execute()

    print("Seed complete")
    print(f"Super admin: {SUPER_EMAIL}")
    print(f"Owner: {OWNER_EMAIL}")
    print(f"Restaurant: {RESTAURANT['name']} /menu/{RESTAURANT['slug']}")


if __name__ == "__main__":
    main()
