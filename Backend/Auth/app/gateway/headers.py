import sys

# Header filtering & injection
DISALLOWED_HEADERS = {
    "host",
    "content-length",
    "authorization"
}

def build_forward_headers(request_headers:dict, user:dict, prefix:str) -> dict:
    headers = {}

    for key, value in request_headers.items():
        if key.lower() not in DISALLOWED_HEADERS:
            headers[key] = value

    # Identify the user to the backend
    headers["X-User-Id"] = str(user["user_id"])
    
    # Extract role from token
    raw_role = user.get("role", "")
    headers["X-User-Roles"] = raw_role

    # Proxy helper headers
    headers["X-Forwarded-Host"] = "localhost:8001"
    headers["X-Forwarded-Proto"] = "http"
    headers["X-Forwarded-For"] = "127.0.0.1"

    # Inject OpenC3 specific authorization
    if prefix and "openc3-api" in prefix:
        headers["Authorization"] = "mos12345"

    # Inject Grafana Auth Proxy headers
    if prefix and "grafana" in prefix:
        headers["X-WEBAUTH-USER"] = user.get("username", str(user["user_id"]))
        
        # LOGGING: See what role 
        # we are actually getting
        print(f"DEBUG: Mapping Grafana role for user {headers['X-WEBAUTH-USER']}. Raw role from token: '{raw_role}'", file=sys.stderr)
        
        # Robust case-insensitive check
        normalized_role = raw_role.upper().strip()
        if normalized_role in ["SUPER_ADMIN", "SUPER ADMIN", "ADMIN", "MISSION_OPERATOR", "MISSION OPERATOR"]:
            headers["X-WEBAUTH-ROLE"] = "Admin"
            print(f"DEBUG: Assigned Grafana role: Admin", file=sys.stderr)
        else:
            headers["X-WEBAUTH-ROLE"] = "Viewer"
            print(f"DEBUG: Assigned Grafana role: Viewer", file=sys.stderr)

    return headers