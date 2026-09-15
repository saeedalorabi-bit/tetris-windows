import requests
from settings import SERVER_URL

PUBLIC_SERVER_URL = "http://176.224.160.251:8000"


def get_server_url():
    try:
        requests.get(f"{SERVER_URL}/leaderboard", timeout=2)
        return SERVER_URL
    except requests.exceptions.RequestException:
        return PUBLIC_SERVER_URL


def register(username, password):
    try:
        resp = requests.post(
            f"{get_server_url()}/register",
            json={"username": username, "password": password},
            timeout=4
        )

        if resp.status_code == 200:
            return True, "Success"

        return False, resp.json().get("detail", "Registration failed.")

    except requests.exceptions.RequestException:
        return False, "Network error: Unable to reach HomeLab server."


def login(username, password):
    try:
        resp = requests.post(
            f"{get_server_url()}/login",
            json={"username": username, "password": password},
            timeout=4
        )

        if resp.status_code == 200:
            data = resp.json()

            token = data.get("access_token") or data.get("token")

            return True, {
                "token": token,
                "high_score": data.get("high_score", 0)
            }

        return False, resp.json().get("detail", "Login failed.")

    except requests.exceptions.RequestException:
        return False, "Network error: Unable to reach HomeLab server."


def get_leaderboard():
    try:
        resp = requests.get(
            f"{get_server_url()}/leaderboard",
            timeout=4
        )

        if resp.status_code == 200:
            data = resp.json()

            if isinstance(data, list):
                return data

            print("ERROR: Server returned payload other than a list.")
            return []

        print(
            f"ERROR: Leaderboard server returned HTTP {resp.status_code}"
        )
        return []

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not connect to leaderboard server: {e}")
        return []

    except Exception as e:
        print(f"ERROR: Unexpected leaderboard error: {e}")
        return []


def submit_score(token, score):
    if not token:
        return score

    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        resp = requests.post(
            f"{get_server_url()}/score",
            json={"score": score},
            headers=headers,
            timeout=4
        )

        if resp.status_code == 200:
            return resp.json().get("high_score", score)

    except requests.exceptions.RequestException:
        pass

    return score