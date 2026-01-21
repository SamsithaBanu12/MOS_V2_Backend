"""
Test script for the c2-Auth API endpoints.

This script demonstrates how to test the authentication endpoints.
You can run this after starting the server with: uvicorn app.main:app --reload

Usage:
    python test_api.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test the health check endpoint."""
    print("\n" + "="*50)
    print("Testing Health Check Endpoint")
    print("="*50)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200


def test_register(email, username, password, role):
    """Test user registration."""
    print("\n" + "="*50)
    print(f"Testing Registration: {email}")
    print("="*50)
    
    payload = {
        "email": email,
        "username": username,
        "password": password,
        "role": role
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 201


def test_login(email, password):
    """Test user login."""
    print("\n" + "="*50)
    print(f"Testing Login: {email}")
    print("="*50)
    
    payload = {
        "email": email,
        "password": password
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=payload)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        print(f"\n✅ Login successful!")
        print(f"Token: {data['token'][:50]}...")
        print(f"Role: {data['role']}")
        print(f"Permissions: {data['permissions']}")
        return data['token']
    else:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return None


def test_invalid_login():
    """Test login with invalid credentials."""
    print("\n" + "="*50)
    print("Testing Invalid Login")
    print("="*50)
    
    payload = {
        "email": "wrong@example.com",
        "password": "wrongpassword"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 401


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("c2-Auth API Test Suite")
    print("="*70)
    print("\nMake sure the server is running: uvicorn app.main:app --reload")
    print("And the database is initialized: python init_db.py")
    
    try:
        # Test health check
        test_health_check()
        
        # Test registration
        test_register(
            email="super_admin@example.com",
            username="super_admin",
            password="securepass123",
            role="SUPER_ADMIN"
        )
        
        # Test registration with user role
        test_register(
            email="operator@example.com",
            username="operator",
            password="userpass123",
            role="OPERATOR"
        )
        
        # Test login
        token = test_login("super_admin@example.com", "securepass123")
        
        # Test invalid login
        test_invalid_login()
        
        # Test duplicate registration
        print("\n" + "="*50)
        print("Testing Duplicate Registration (Should Fail)")
        print("="*50)
        test_register(
            email="super_admin@example.com",
            username="super_admin_duplicate",
            password="password123",
            role="SUPER_ADMIN"
        )
        
        print("\n" + "="*70)
        print("✅ All tests completed!")
        print("="*70)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the server.")
        print("Make sure the server is running: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main()
