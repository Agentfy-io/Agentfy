from flask import Flask, request, jsonify
import logging

app = Flask(__name__)

# Configure logging to terminal and file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('webhook.log'),  # Log to file for persistence
        logging.StreamHandler()  # Log to terminal
    ]
)

# Your verify token from Instagram webhook settings
VERIFY_TOKEN = "Test123"

@app.route('/callback', methods=['GET'])
def webhook_verify():
    try:
        # Extract query parameters
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        # Log all incoming query parameters
        logging.info(f"Received GET request: {request.args}")
        logging.info(f"hub.mode: {mode}")
        logging.info(f"hub.verify_token: {token}")
        logging.info(f"hub.challenge: {challenge}")

        # Check if mode and token are present
        if mode and token:
            if mode == 'subscribe' and token == VERIFY_TOKEN:
                logging.info("Webhook verification successful")
                # Return the challenge as plain text (Instagram expects this)
                return challenge, 200, {'Content-Type': 'text/plain'}
            else:
                logging.error("Verification failed: Invalid mode or token")
                return jsonify({"error": "Invalid mode or token"}), 403
        else:
            logging.error("Verification failed: Missing mode or token")
            return jsonify({"error": "Missing mode or token"}), 400

    except Exception as e:
        logging.error(f"Error in webhook_verify: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/callback', methods=['POST'])
def webhook_event():
    try:
        # Log incoming POST requests (for future webhook events)
        data = request.get_json() or {}
        logging.info(f"Received POST request: {data}")
        return jsonify({"status": "received"}), 200
    except Exception as e:
        logging.error(f"Error in webhook_event: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/')
def home():
    # Simple endpoint to verify server is running
    logging.info("Received request to root endpoint")
    return "Server is running!", 200

if __name__ == '__main__':
    logging.info("Starting Flask server on port 8000")
    app.run(host='0.0.0.0', port=8000, debug=True)