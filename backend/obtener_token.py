import requests


def obtener_token(email, password):
    """Request a JWT access token using the given credentials.

    Args:
        email (str): User email address.
        password (str): User password.

    Returns:
        str | None: Access token string if authentication succeeds, otherwise ``None``.
    """
    url = "http://localhost:8000/api/token/"
    payload = {"email": email, "password": password}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        print("Access token:")
        print(data["access"])
        return data["access"]
    print("Error:", response.status_code, response.text)
    return None
