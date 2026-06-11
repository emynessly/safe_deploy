import requests

BASE_URL = "http://127.0.0.1:8000"

response = requests.get(f"{BASE_URL}/files/2", headers={"username": "alice"}, timeout=5)
print("Test 1 (IDOR):", response.status_code == 404)

response = requests.get(f"{BASE_URL}/files/1", headers={"username": "alice"}, timeout=5)
print("Test 2 (Access):", response.status_code == 200)

response = requests.delete(f"{BASE_URL}/files/2", headers={"username": "admin"}, timeout=5)
print("Test 3 (Admin):", response.status_code == 200)

response = requests.get(f"{BASE_URL}/files/2", headers={"username": "admin"}, timeout=5)
print("File deleted:", response.status_code == 404)