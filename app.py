from flask import Flask, request, jsonify, redirect
import os
import requests
from datetime import datetime

app = Flask(__name__)

VERIFY_TOKEN = "my_verify_token"

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

messages = []


@app.route("/")
def home():
    return """
    <h2>WhatsApp API is Running ✅</h2>
    <p><a href="/dashboard">Open WhatsApp Inbox</a></p>
    """


@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200

        return "Verification failed", 403

    data = request.get_json(silent=True) or {}
    print(data)

    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):

                value = change.get("value", {})
                contacts = value.get("contacts", [])

                for msg in value.get("messages", []):

                    phone = msg.get("from", "")
                    msg_type = msg.get("type", "unknown")

                    name = phone
                    if contacts:
                        name = contacts[0].get("profile", {}).get("name", phone)

                    text = ""
                    if msg_type == "text":
                        text = msg.get("text", {}).get("body", "")

                    messages.append({
                        "direction": "incoming",
                        "name": name,
                        "phone": phone,
                        "message": text,
                        "time": datetime.now().strftime("%d-%m-%Y %I:%M %p")
                    })

    except Exception as e:
        print("Webhook Error:", e)

    return "EVENT_RECEIVED", 200


@app.route("/send-message", methods=["POST"])
def send_message():

    phone = request.form.get("phone", "").strip()
    text = request.form.get("message", "").strip()

    if not phone or not text:
        return redirect("/dashboard")

    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        return "Missing WHATSAPP_TOKEN or PHONE_NUMBER_ID", 500

    url = f"https://graph.facebook.com/v26.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {
            "body": text
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=20
    )

    print("SEND RESPONSE:", response.status_code, response.text)

    if response.ok:
        messages.append({
            "direction": "outgoing",
            "name": "You",
            "phone": phone,
            "message": text,
            "time": datetime.now().strftime("%d-%m-%Y %I:%M %p")
        })
    else:
        return f"Send failed: {response.text}", response.status_code

    return redirect("/dashboard")


@app.route("/dashboard")
def dashboard():

    customers = {}

    for msg in messages:
        phone = msg["phone"]

        if phone not in customers:
            customers[phone] = {
                "name": msg["name"],
                "phone": phone,
                "messages": []
            }

        customers[phone]["messages"].append(msg)

    cards = ""

    for phone, customer in reversed(list(customers.items())):

        chat = ""

        for msg in customer["messages"]:

            bubble_class = (
                "outgoing"
                if msg["direction"] == "outgoing"
                else "incoming"
            )

            chat += f"""
            <div class="bubble {bubble_class}">
                <div>{msg['message']}</div>
                <small>{msg['time']}</small>
            </div>
            """

        cards += f"""
        <div class="chat-card">

            <div class="customer-header">
                <strong>{customer['name']}</strong>
                <div class="phone">{phone}</div>
            </div>

            <div class="conversation">
                {chat}
            </div>

            <form method="POST" action="/send-message" class="reply-form">

                <input type="hidden" name="phone" value="{phone}">

                <input
                    type="text"
                    name="message"
                    placeholder="Type a reply..."
                    required
                >

                <button type="submit">Send</button>

            </form>

        </div>
        """

    if not cards:
        cards = """
        <div class="empty">
            No messages yet.
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>

        <title>WhatsApp Inbox</title>

        <meta name="viewport"
              content="width=device-width, initial-scale=1">

        <style>

            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f3f4f6;
            }}

            .header {{
                background: #111827;
                color: white;
                padding: 18px;
            }}

            .header h2 {{
                margin: 0;
                font-size: 26px;
            }}

            .status {{
                display: inline-block;
                margin-top: 10px;
                background: #dcfce7;
                color: #166534;
                padding: 7px 12px;
                border-radius: 20px;
            }}

            .container {{
                max-width: 800px;
                margin: auto;
                padding: 15px;
            }}

            .chat-card {{
                background: white;
                border-radius: 14px;
                margin-bottom: 18px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,.08);
            }}

            .customer-header {{
                padding: 15px;
                border-bottom: 1px solid #eee;
                font-size: 18px;
            }}

            .phone {{
                font-size: 13px;
                color: #6b7280;
                margin-top: 3px;
            }}

            .conversation {{
                background: #efeae2;
                padding: 15px;
                min-height: 120px;
            }}

            .conversation::after {{
                content: "";
                display: block;
                clear: both;
            }}

            .bubble {{
                max-width: 80%;
                padding: 10px 12px;
                border-radius: 10px;
                margin-bottom: 10px;
                clear: both;
                word-wrap: break-word;
            }}

            .incoming {{
                float: left;
                background: white;
            }}

            .outgoing {{
                float: right;
                background: #d9fdd3;
            }}

            .bubble small {{
                display: block;
                font-size: 10px;
                color: #777;
                margin-top: 5px;
            }}

            .reply-form {{
                display: flex;
                gap: 8px;
                padding: 12px;
            }}

            .reply-form input {{
                flex: 1;
                min-width: 0;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 24px;
                font-size: 16px;
            }}

            .reply-form button {{
                border: 0;
                background: #16a34a;
                color: white;
                padding: 10px 18px;
                border-radius: 24px;
                font-weight: bold;
            }}

            .empty {{
                background: white;
                padding: 30px;
                border-radius: 14px;
                text-align: center;
            }}

        </style>

    </head>

    <body>

        <div class="header">
            <h2>WhatsApp Inbox</h2>
            <div class="status">● Webhook Connected</div>
        </div>

        <div class="container">
            {cards}
        </div>

    </body>
    </html>
    """


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
