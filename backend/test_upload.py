import requests

try:
    with open('aws_test_data.csv', 'rb') as f:
        files = {'file': ('aws_test_data.csv', f, 'text/csv')}
        response = requests.post('http://localhost:8080/calculate-cost', files=files)
        print("Status Code:", response.status_code)
        
        try:
             import json
             print("JSON Response:", json.dumps(response.json(), indent=2))
        except Exception:
             print("Text Response:", response.text)
except Exception as e:
    print(f"Error: {e}")
