#!/usr/bin/env python3
"""
CRUD Verification Test Script
Tests all backend fixes for category and item creation/retrieval.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Test data
SUPER_ADMIN_TOKEN = None
RESTAURANT_ID = None
CATEGORY_ID = None
ITEM_ID = None

def log_test(test_name, status, details=""):
    """Pretty print test results"""
    symbol = "✅" if status else "❌"
    print(f"\n{symbol} {test_name}")
    if details:
        print(f"   {details}")

def test_get_restaurants():
    """GET /super/restaurants - Get all restaurants"""
    print("\n" + "="*60)
    print("TEST 1: Getting restaurants")
    print("="*60)
    
    try:
        url = f"{BASE_URL}/super/restaurants"
        response = requests.get(url)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                global RESTAURANT_ID
                RESTAURANT_ID = data[0]["id"]
                log_test("GET /super/restaurants", True, f"Found {len(data)} restaurants. Using restaurant_id: {RESTAURANT_ID}")
                return True
            else:
                log_test("GET /super/restaurants", False, "No restaurants found")
                return False
        else:
            log_test("GET /super/restaurants", False, f"HTTP {response.status_code}")
            return False
    except Exception as e:
        log_test("GET /super/restaurants", False, str(e))
        return False

def test_get_categories():
    """GET /super/restaurants/:id/categories - Get categories for restaurant"""
    print("\n" + "="*60)
    print("TEST 2: Getting categories for restaurant")
    print("="*60)
    
    if not RESTAURANT_ID:
        log_test("GET /super/restaurants/:id/categories", False, "No restaurant_id available")
        return False
    
    try:
        url = f"{BASE_URL}/super/restaurants/{RESTAURANT_ID}/categories"
        response = requests.get(url)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)[:500]}...")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                log_test("GET /super/restaurants/:id/categories", True, f"Found {len(data)} categories")
                if len(data) > 0:
                    global CATEGORY_ID
                    CATEGORY_ID = data[0]["id"]
                return True
            else:
                log_test("GET /super/restaurants/:id/categories", False, "Response is not a list")
                return False
        else:
            log_test("GET /super/restaurants/:id/categories", False, f"HTTP {response.status_code}")
            return False
    except Exception as e:
        log_test("GET /super/restaurants/:id/categories", False, str(e))
        return False

def test_create_category():
    """POST /super/categories - Create a new category"""
    print("\n" + "="*60)
    print("TEST 3: Creating a new category")
    print("="*60)
    
    if not RESTAURANT_ID:
        log_test("POST /super/categories", False, "No restaurant_id available")
        return False
    
    payload = {
        "restaurant_id": RESTAURANT_ID,
        "name": f"Test Category {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "display_order": 99,
        "icon_emoji": "🍕"
    }
    
    try:
        url = f"{BASE_URL}/super/categories"
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            global CATEGORY_ID
            CATEGORY_ID = data.get("id")
            log_test("POST /super/categories", True, f"Created category: {CATEGORY_ID}")
            return True
        else:
            log_test("POST /super/categories", False, f"HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("POST /super/categories", False, str(e))
        return False

def test_get_items():
    """GET /super/restaurants/:id/items - Get items for restaurant"""
    print("\n" + "="*60)
    print("TEST 4: Getting menu items for restaurant")
    print("="*60)
    
    if not RESTAURANT_ID:
        log_test("GET /super/restaurants/:id/items", False, "No restaurant_id available")
        return False
    
    try:
        url = f"{BASE_URL}/super/restaurants/{RESTAURANT_ID}/items"
        response = requests.get(url)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)[:500]}...")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                log_test("GET /super/restaurants/:id/items", True, f"Found {len(data)} items")
                if len(data) > 0:
                    global ITEM_ID
                    ITEM_ID = data[0]["id"]
                return True
            else:
                log_test("GET /super/restaurants/:id/items", False, "Response is not a list")
                return False
        else:
            log_test("GET /super/restaurants/:id/items", False, f"HTTP {response.status_code}")
            return False
    except Exception as e:
        log_test("GET /super/restaurants/:id/items", False, str(e))
        return False

def test_create_item():
    """POST /super/items - Create a new menu item"""
    print("\n" + "="*60)
    print("TEST 5: Creating a new menu item")
    print("="*60)
    
    if not RESTAURANT_ID or not CATEGORY_ID:
        log_test("POST /super/items", False, "Missing restaurant_id or category_id")
        return False
    
    payload = {
        "restaurant_id": RESTAURANT_ID,
        "category_id": CATEGORY_ID,
        "name": f"Test Item {datetime.now().strftime('%Y%m%d%H%M%S')}",
        "description": "A test menu item",
        "price": 199.99,
        "mrp_price": 249.99,
        "is_available": True,
        "is_veg": True,
        "is_special": False,
        "is_bestseller": False,
        "display_order": 99
    }
    
    try:
        url = f"{BASE_URL}/super/items"
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, json=payload)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            global ITEM_ID
            ITEM_ID = data.get("id")
            log_test("POST /super/items", True, f"Created item: {ITEM_ID}")
            return True
        else:
            log_test("POST /super/items", False, f"HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("POST /super/items", False, str(e))
        return False

def test_public_menu():
    """GET /menu/:slug - Verify public menu endpoint works"""
    print("\n" + "="*60)
    print("TEST 6: Getting public menu")
    print("="*60)
    
    # First get a restaurant to find its slug
    try:
        url = f"{BASE_URL}/super/restaurants"
        response = requests.get(url)
        
        if response.status_code == 200:
            restaurants = response.json()
            if len(restaurants) > 0:
                slug = restaurants[0].get("slug")
                if slug:
                    menu_url = f"{BASE_URL}/menu/{slug}"
                    menu_response = requests.get(menu_url)
                    
                    print(f"Status Code: {menu_response.status_code}")
                    if menu_response.status_code == 200:
                        menu_data = menu_response.json()
                        print(f"Response keys: {list(menu_data.keys())}")
                        log_test("GET /menu/:slug", True, f"Public menu accessible for slug: {slug}")
                        return True
                    else:
                        log_test("GET /menu/:slug", False, f"HTTP {menu_response.status_code}")
                        return False
    except Exception as e:
        log_test("GET /menu/:slug", False, str(e))
        return False
    
    log_test("GET /menu/:slug", False, "Could not find restaurant slug")
    return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("BACKEND CRUD VERIFICATION TESTS")
    print("="*60)
    
    results = []
    
    results.append(("GET /super/restaurants", test_get_restaurants()))
    results.append(("GET /super/restaurants/:id/categories", test_get_categories()))
    results.append(("POST /super/categories", test_create_category()))
    results.append(("GET /super/restaurants/:id/items", test_get_items()))
    results.append(("POST /super/items", test_create_item()))
    results.append(("GET /menu/:slug", test_public_menu()))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        symbol = "✅" if result else "❌"
        print(f"{symbol} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Backend fixes are working correctly.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review the output above for details.")

if __name__ == "__main__":
    main()
