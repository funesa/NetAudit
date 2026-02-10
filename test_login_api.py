import requests
import json

url = 'http://localhost:5000/login'
headers = {'Content-Type': 'application/json'}
data = {
    'username': 'pofjunior',
    'password': 'admin'
}

print(f"Testing login to {url} with user 'pofjunior'...")

try:
    response = requests.post(url, headers=headers, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200 and response.json().get('success'):
        print("LOGIN SUCCESSFUL!")
    else:
        print("LOGIN FAILED!")
        
except Exception as e:
    print(f"Request Error: {e}")
