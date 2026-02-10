import requests
try:
    r = requests.get('http://127.0.0.1:5000/api/dashboard/stats', timeout=5)
    print(f"Stats Status: {r.status_code}")
    print(f"Stats Data: {r.json()}")
except Exception as e:
    print(f"Error: {e}")
