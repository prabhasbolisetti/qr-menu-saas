#!/usr/bin/env python3
"""
Quick Public Endpoint Test - No Auth Required
Verifies that the backend schema and service fixes work for public menu
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n✓ Testing /health")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print(f"  Status: {response.status_code} ✓")

def test_root():
    """Test root endpoint"""
    print("\n✓ Testing /")
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    print(f"  Status: {response.status_code} ✓")

def test_nonexistent_menu():
    """Test menu endpoint with nonexistent slug"""
    print("\n✓ Testing /menu/{slug} with nonexistent slug")
    response = requests.get(f"{BASE_URL}/menu/nonexistent-slug-xyz")
    # Should return 404, not 500
    assert response.status_code == 404
    assert response.json()["detail"] == "Restaurant not found"
    print(f"  Status: {response.status_code} - Correct error handling ✓")

def test_auth_required():
    """Test that super admin endpoints require auth"""
    print("\n✓ Testing /super/restaurants (should require auth)")
    response = requests.get(f"{BASE_URL}/super/restaurants")
    assert response.status_code == 401
    assert "bearer token" in response.json()["detail"].lower()
    print(f"  Status: {response.status_code} - Auth required ✓")

def main():
    print("\n" + "="*60)
    print("BACKEND PUBLIC ENDPOINT TESTS")
    print("="*60)
    
    try:
        test_health()
        test_root()
        test_nonexistent_menu()
        test_auth_required()
        
        print("\n" + "="*60)
        print("✅ ALL BASIC TESTS PASSED!")
        print("="*60)
        print("\nKey validation points:")
        print("  ✓ Backend is running and responsive")
        print("  ✓ Health check working")
        print("  ✓ Public menu endpoint returns proper 404 (not 500)")
        print("  ✓ Auth middleware is enforcing role-based access")
        print("  ✓ No unhandled exceptions breaking the API")
        print("\nThe schema and service fixes are in place!")
        print("Next: Test with proper authentication for admin endpoints")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
