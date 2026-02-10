import requests
try:
    # Test simple endpoint
    r = requests.get('http://127.0.0.1:5000/api/monitoring/overview', timeout=5)
    print(f"Overview Status: {r.status_code}")
    
    # Test history endpoint
    r = requests.get('http://127.0.0.1:5000/api/metrics/history', timeout=10)
    print(f"History Status: {r.status_code}")
except Exception as e:
    print(f"Error: {e}")
