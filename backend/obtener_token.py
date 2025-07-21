import requests

def obtener_token(email, password):
    url = "http://localhost:8000/api/token/"
    payload = {
        "email": email,
        "password": password
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        print("Access token:")
        print(data["access"])
        return data["access"]
    else:
        print("Error:", response.status_code, response.text)
        return None
