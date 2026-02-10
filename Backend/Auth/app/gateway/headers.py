# Header filtering & injection
DISALLOWED_HEADERS = {
    "authorization",
    "cookie",
    "host",
    "content-length"
}

def build_forward_headers(request_headers:dict, user:dict, prefix:str) -> dict:
    headers = {}

    for key, value in request_headers.items():
        if key.lower() not in DISALLOWED_HEADERS:
            headers[key] = value

    headers["X-User-Id"] = str(user["user_id"])
    headers["X-User-Roles"] = str(user.get("role", ""))

    # Inject OpenC3 specific authorization only for OpenC3 routes
    if "openc3-api" in prefix:
        headers["Authorization"] = "mos12345"

    return headers