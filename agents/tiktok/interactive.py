import requests
import webbrowser
import http.server
import socketserver
import urllib.parse
import secrets
import hashlib
import base64

# TikTok API credentials (replace with your own)
CLIENT_KEY = "sbawvm8oh1mwx452w0"  # Your Client Key
CLIENT_SECRET = "qoYJpv7ATdmaYFboYKoQxnFSYglrZufS"  # From TikTok Developer Portal
REDIRECT_URI = "https://c5c5-172-117-224-157.ngrok-free.app"  # Must match Developer Portal
VIDEO_URL = "https://your-verified-domain.com/video.mp4"  # Verified domain

# Step 1: Generate code_verifier and code_challenge for PKCE
def generate_pkce_pair():
    # Generate a random code_verifier (43-128 characters)
    code_verifier = secrets.token_urlsafe(64)
    # Create code_challenge: base64-url-encoded SHA-256 hash of code_verifier
    sha256_hash = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(sha256_hash).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge

# Step 2: Generate authorization URL with PKCE
def get_authorization_url(code_challenge):
    url = "https://www.tiktok.com/v2/auth/authorize/"
    csrf_state = secrets.token_hex(16)  # Secure random CSRF state
    params = {
        "client_key": CLIENT_KEY,
        "scope": "user.info.basic",
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": csrf_state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    auth_url = f"{url}?{urllib.parse.urlencode(params)}"
    return auth_url, csrf_state

# Step 3: Set up a local server to capture the authorization code
class OAuthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params and "state" in params:
            self.server.auth_code = params["code"][0]
            self.server.csrf_state = params["state"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Authorization successful! You can close this window.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Error: No authorization code or state received.")

def get_auth_code(expected_csrf_state):
    PORT = 8000
    with socketserver.TCPServer(("", PORT), OAuthHandler) as httpd:
        print(f"Local server started at http://localhost:{PORT}")
        code_verifier, code_challenge = generate_pkce_pair()
        auth_url, _ = get_authorization_url(code_challenge)
        print(f"Authorization URL: {auth_url}")
        webbrowser.open(auth_url)
        httpd.handle_request()  # Handle one request (the callback)
        if httpd.csrf_state != expected_csrf_state:
            raise Exception("CSRF state mismatch. Possible attack.")
        return httpd.auth_code, code_verifier

# Step 4: Exchange authorization code for access token
def get_access_token(auth_code, code_verifier):
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    data = {
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code": urllib.parse.unquote(auth_code),  # Decode the code
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["data"]["access_token"]
    else:
        raise Exception(f"Failed to get access token: {response.json()}")

# Step 5: Post a video to TikTok
def post_video(access_token):
    url = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "source_info": {
            "source": "PULL_FROM_URL",
            "video_url": VIDEO_URL
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        publish_id = response.json().get("data", {}).get("publish_id")
        print(f"Video posted successfully! Publish ID: {publish_id}")
    else:
        print(f"Failed to post video: {response.json()}")

# Main execution
def main():
    try:
        # Generate CSRF state
        csrf_state = secrets.token_hex(16)
        # Get authorization code and code_verifier
        auth_code, code_verifier = get_auth_code(csrf_state)
        print(f"Authorization code: {auth_code}")
        # Get access token
        access_token = get_access_token(auth_code, code_verifier)
        print(f"Access token: {access_token}")
        # Post video
        post_video(access_token)
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()