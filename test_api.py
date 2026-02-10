import requests
try:
    r = requests.get('http://127.0.0.1:5000/api/metrics/history', timeout=10)
    print(f"Status: {r.status_code}")
    data = r.json()
    print(f"Success: {data.get('success')}")
    print(f"Data length: {len(data.get('data', []))}")
    if data.get('data'):
        print(f"Sample: {data.get('data')[0]}")
except Exception as e:
    print(f"Error: {e}")
