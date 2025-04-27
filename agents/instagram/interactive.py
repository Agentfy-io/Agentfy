import requests
import json
from flask import Flask, request, redirect
import webbrowser
import os

# Configuration - Replace with your Meta Developer app details
APP_ID = "1702316543706212"  # Meta Developer app ID
APP_SECRET = "8348e7300cf4c810141f0dc7f1c13da5"  # Meta Developer app secret
REDIRECT_URI = "https://275d-172-117-224-157.ngrok-free.app/callback"  # Must match the redirect URI in your app settings
BASE_URL = "https://graph.facebook.com/v21.0"
AUTH_URL = "https://api.instagram.com/oauth/authorize"
TOKEN_URL = "https://api.instagram.com/oauth/access_token"

# Flask app for handling OAuth redirect
app = Flask(__name__)
access_token = None
ig_user_id = None

# Function to get Instagram login URL
def get_login_url():
    scope = "instagram_manage_messages"
    return (f"{AUTH_URL}?client_id={APP_ID}&redirect_uri={REDIRECT_URI}&scope={scope}&response_type=code")

# Flask route for OAuth callback
@app.route('/callback')
def callback():
    global access_token, ig_user_id
    code = request.args.get('code')
    if not code:
        return "Error: No code received"

    # Exchange code for short-lived access token
    payload = {
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
        "code": code
    }
    response = requests.post(TOKEN_URL, data=payload)
    result = response.json()

    if "access_token" in result:
        short_lived_token = result["access_token"]
        user_id = result["user_id"]

        # Exchange for long-lived token
        exchange_url = f"{BASE_URL}/oauth/access_token"
        exchange_payload = {
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": short_lived_token
        }
        exchange_response = requests.get(exchange_url, params=exchange_payload)
        exchange_result = exchange_response.json()

        if "access_token" in exchange_result:
            access_token = exchange_result["access_token"]

            # Get Instagram Business/Creator account ID
            user_url = f"{BASE_URL}/{user_id}?fields=instagram_business_account&access_token={access_token}"
            user_response = requests.get(user_url)
            user_result = user_response.json()

            if "instagram_business_account" in user_result:
                ig_user_id = user_result["instagram_business_account"]["id"]
                print(f"Successfully authenticated! Access Token: {access_token}, IG User ID: {ig_user_id}")
                return "Authentication successful! You can now close this window."
            else:
                return "Error: No Instagram Business/Creator account found"
        else:
            return f"Error exchanging token: {exchange_result}"
    else:
        return f"Error getting token: {result}"

# Function to post an image
def post_image(image_url, caption):
    post_url = f"{BASE_URL}/{ig_user_id}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": access_token
    }
    response = requests.post(post_url, data=payload)
    result = response.json()

    if "id" in result:
        creation_id = result["id"]
        publish_url = f"{BASE_URL}/{ig_user_id}/media_publish"
        publish_payload = {
            "creation_id": creation_id,
            "access_token": access_token
        }
        publish_response = requests.post(publish_url, data=publish_payload)
        publish_result = publish_response.json()

        if "id" in publish_result:
            print("Successfully posted! Post ID:", publish_result["id"])
            return publish_result["id"]
        else:
            print("Failed to publish:", publish_result)
            return None
    else:
        print("Failed to create media:", result)
        return None

# Function to comment on a post
def comment_on_post(media_id, comment_text):
    comment_url = f"{BASE_URL}/{media_id}/comments"
    payload = {
        "message": comment_text,
        "access_token": access_token
    }
    response = requests.post(comment_url, data=payload)
    result = response.json()

    if "id" in result:
        print("Successfully commented! Comment ID:", result["id"])
        return result["id"]
    else:
        print("Failed to comment:", result)
        return None

# Function to send a direct message
def send_direct_message(recipient_id, message_text):
    dm_url = f"{BASE_URL}/{ig_user_id}/messages"
    payload = {
        "recipient": json.dumps({"id": recipient_id}),
        "message": json.dumps({"text": message_text}),
        "access_token": access_token
    }
    response = requests.post(dm_url, data=payload)
    result = response.json()

    if "id" in result:
        print("Successfully sent DM! Message ID:", result["id"])
        return result["id"]
    else:
        print("Failed to send DM:", result)
        return None

# Main function to run the app and perform actions
def main():
    # Start Flask server in a separate thread
    import threading
    server_thread = threading.Thread(target=lambda: app.run(port=8000))
    server_thread.daemon = True
    server_thread.start()

    # Open browser for Instagram Login
    login_url = get_login_url()
    print("Please visit this URL to log in:", login_url)
    webbrowser.open(login_url)

    # Wait for authentication to complete
    while access_token is None or ig_user_id is None:
        pass

    # Perform Instagram actions
    image_url = "https://example.com/public-image.jpg"  # Replace with a public image URL
    caption = "Testing Instagram API! #Python"
    comment_text = "Nice post!"
    recipient_id = "RECIPIENT_IG_USER_ID"  # Replace with recipient's Instagram user ID
    message_text = "Test DM via Graph API"

    print("\nPosting image...")
    post_id = post_image(image_url, caption)

    if post_id:
        print("\nCommenting on post...")
        comment_on_post(post_id, comment_text)

    print("\nSending direct message...")
    send_direct_message(recipient_id, message_text)

if __name__ == "__main__":
    main()