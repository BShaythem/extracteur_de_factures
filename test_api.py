import requests
import json

# Test registration
url = "http://localhost:5000/api/auth/register"
data = {
    "username": "haythem",
    "password": "haythem"
}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Headers: {response.headers}")
except Exception as e:
    print(f"Error: {e}") 