"""
LinkedIn API OAuth 2.0 Setup & Token Management

This module handles:
  1. One-time authorization flow to get access + refresh tokens
  2. Auto-refresh of expired tokens
  3. Profile/person URN lookup

Prerequisites (one-time setup, ~2 minutes):
  1. Go to https://www.linkedin.com/developers/apps
  2. Click "Create App"
  3. Fill in app name, LinkedIn Page (use your profile), URL (any), email
  4. Go to the "Auth" tab
  5. Add redirect URL: http://localhost:9876/callback
  6. Under "Products", request access to:
     - "Share on LinkedIn" (sign the agreement)
     - "Marketing Developer Platform" (if prompted)
  7. Copy your Client ID and Client Secret from the "Auth" tab

Usage:
  # First-time: authorize and get tokens
  python3 linkedin_api.py --setup --client-id YOUR_ID --client-secret YOUR_SECRET

  # Test connection
  python3 linkedin_api.py --test

  # Get profile info
  python3 linkedin_api.py --profile

Tokens are saved to linkedin_tokens.json (auto-refreshed).
"""

import os, sys, json, time, argparse, webbrowser, urllib.parse
from pathlib import Path

try:
    import requests
except ImportError:
    os.system("pip install requests --break-system-packages -q")
    import requests

try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
except ImportError:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE, "linkedin_tokens.json")

# OAuth 2.0 endpoints
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
SCOPES = "w_member_social openid profile email"


def load_tokens():
    """Load tokens from file."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return json.load(f)
    return None


def save_tokens(tokens):
    """Save tokens to file."""
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    # Ensure it's gitignored
    gitignore = os.path.join(BASE, ".gitignore")
    if os.path.exists(gitignore):
        with open(gitignore) as f:
            content = f.read()
        if "linkedin_tokens.json" not in content:
            with open(gitignore, "a") as f:
                f.write("linkedin_tokens.json\n")


def is_token_expired(tokens):
    """Check if access token is expired."""
    if not tokens:
        return True
    expires_at = tokens.get("expires_at", 0)
    # Refresh 5 minutes early
    return time.time() > (expires_at - 300)


def refresh_access_token(tokens):
    """Refresh the access token using the refresh token."""
    client_id = tokens.get("client_id", "")
    client_secret = tokens.get("client_secret", "")
    refresh_token = tokens.get("refresh_token", "")

    if not refresh_token:
        print("❌ No refresh token available. Run --setup again.")
        return None

    resp = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    })

    if resp.status_code != 200:
        print(f"❌ Token refresh failed: {resp.json().get('error_description', resp.text)}")
        return None

    data = resp.json()
    tokens["access_token"] = data["access_token"]
    tokens["expires_at"] = time.time() + data.get("expires_in", 5184000)  # default 60 days
    if "refresh_token" in data:
        tokens["refresh_token"] = data["refresh_token"]
    save_tokens(tokens)
    print("✅ Token refreshed successfully.")
    return tokens


def get_valid_token():
    """Get a valid access token, refreshing if needed."""
    tokens = load_tokens()
    if not tokens:
        return None, "No tokens found. Run --setup first."
    if is_token_expired(tokens):
        print("Token expired, refreshing...")
        tokens = refresh_access_token(tokens)
        if not tokens:
            return None, "Token refresh failed."
    return tokens, None


def run_oauth_flow(client_id, client_secret):
    """Run the OAuth 2.0 authorization code flow with local callback server."""
    redirect_uri = "http://localhost:9876/callback"
    
    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "state": "linkedin_pipeline",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(auth_params)}"
    
    print(f"\n{'='*60}")
    print("🔗 LinkedIn OAuth Authorization")
    print(f"{'='*60}")
    print(f"\nOpening browser for LinkedIn authorization...")
    print(f"If it doesn't open, visit:\n  {auth_url}\n")
    
    # Start local server to catch callback
    auth_code = [None]
    
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/callback"):
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                if "code" in params:
                    auth_code[0] = params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"""
                    <html><body style="font-family:sans-serif;text-align:center;padding:50px">
                    <h1>✅ Authorization Successful!</h1>
                    <p>You can close this tab and return to the terminal.</p>
                    </body></html>
                    """)
                else:
                    error = params.get("error", ["unknown"])[0]
                    self.send_response(400)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(f"<html><body><h1>❌ Error: {error}</h1></body></html>".encode())
        
        def log_message(self, format, *args):
            pass  # Suppress server logs
    
    server = HTTPServer(("localhost", 9876), CallbackHandler)
    
    # Open browser
    try:
        webbrowser.open(auth_url)
    except:
        print(f"  Manual URL: {auth_url}")
    
    print("⏳ Waiting for authorization... (this tab will auto-close)")
    
    # Wait for callback (timeout 5 minutes)
    server.timeout = 1
    start_time = time.time()
    while auth_code[0] is None and (time.time() - start_time) < 300:
        server.handle_request()
    
    server.server_close()
    
    if not auth_code[0]:
        print("❌ Authorization timed out.")
        return None
    
    print("✅ Authorization code received. Exchanging for tokens...")
    
    # Exchange code for tokens
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": auth_code[0],
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    })
    
    if resp.status_code != 200:
        error_data = resp.json()
        print(f"❌ Token exchange failed: {error_data.get('error_description', resp.text)}")
        return None
    
    data = resp.json()
    tokens = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "expires_at": time.time() + data.get("expires_in", 5184000),
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    save_tokens(tokens)
    print(f"✅ Tokens saved to {TOKEN_FILE}")
    print(f"   Access token expires in ~{data.get('expires_in', 5184000)//86400} days")
    return tokens


def get_profile_urn(access_token):
    """Get the user's person URN (needed for posting)."""
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    if resp.status_code != 200:
        print(f"❌ Profile lookup failed: {resp.text}")
        return None
    
    data = resp.json()
    sub = data.get("sub", "")
    name = data.get("name", "")
    email = data.get("email", "")
    print(f"✅ Profile: {name} ({email})")
    print(f"   URN: {sub}")
    return sub


def test_connection():
    """Test the LinkedIn API connection."""
    tokens, err = get_valid_token()
    if err:
        print(f"❌ {err}")
        return
    
    resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Connected to LinkedIn API")
        print(f"   User: {data.get('name', 'unknown')}")
        print(f"   Email: {data.get('email', 'unknown')}")
        expires_in = max(0, int(tokens.get("expires_at", 0) - time.time()))
        print(f"   Token expires in: {expires_in // 3600}h {expires_in % 3600 // 60}m")
    else:
        print(f"❌ API call failed: {resp.status_code} - {resp.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LinkedIn API OAuth 2.0 Management")
    parser.add_argument("--setup", action="store_true", help="Run first-time OAuth setup")
    parser.add_argument("--client-id", help="LinkedIn App Client ID")
    parser.add_argument("--client-secret", help="LinkedIn App Client Secret")
    parser.add_argument("--test", action="store_true", help="Test API connection")
    parser.add_argument("--profile", action="store_true", help="Get profile URN")
    
    args = parser.parse_args()
    
    if args.setup:
        if not args.client_id or not args.client_secret:
            print("❌ --client-id and --client-secret are required for --setup")
            print("\nGet them from: https://www.linkedin.com/developers/apps → Your App → Auth tab")
            sys.exit(1)
        run_oauth_flow(args.client_id, args.client_secret)
    elif args.test:
        test_connection()
    elif args.profile:
        tokens, err = get_valid_token()
        if err:
            print(f"❌ {err}")
        else:
            get_profile_urn(tokens["access_token"])
    else:
        parser.print_help()