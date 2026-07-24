from flask import Flask, request

from app.handlers.webhook_events import handle_webhook_payload
from config import VERIFY_TOKEN

app = Flask(__name__)


@app.route("/")
def home():
    return "🚀 Alyan Order System is Running"


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    try:
        data = request.get_json(silent=True) or {}

        print("=" * 50)
        print("📩 Incoming Webhook")
        print(data)
        print("=" * 50)

        handle_webhook_payload(data)

        return "EVENT_RECEIVED", 200
    except Exception as exc:
        print(f"Error while processing webhook event: {exc}")
        return "EVENT_RECEIVED", 200