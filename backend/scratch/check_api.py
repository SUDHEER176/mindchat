import requests
try:
    r = requests.get('http://127.0.0.1:5000/')
    print(f"Status: {r.status_code}")
    print(f"Body: {r.json()}")
except Exception as e:
    print(f"Failed: {e}")
