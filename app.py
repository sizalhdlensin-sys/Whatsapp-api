from flask import Flask, request, redirect
import os
import requests
from datetime import datetime

app = Flask(__name__)

VERIFY_TOKEN = "my_verify_token"

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

# Temporary storage
# Note: Render restart/redeploy hone par ye history clear ho sakti hai.
messages = []


AUTO_REPLY_MESSAGE = """This is an automated message.
Please contact our Customer Care team at +91 90676 87813 for further assistance.

Thank you."""


def send_whatsapp_message(phone, text):
    """
    Sends a normal WhatsApp text message using Meta WhatsApp Cloud API.
    """

    if not WHATSAPP_TOKEN:
        print("ERROR: WHATSAPP_TOKEN is missing")
        return False, "WHATSAPP_TOKEN missing"

    if not PHONE_NUMBER_ID:
        print("ERROR: PHONE_NUMBER_ID is missing")
        return False, "PHONE_NUMBER_ID missing"

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

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=20
        )

        print(
            "WHATSAPP SEND RESPONSE:",
            response.status_code,
            response.text
        )

        if response.ok:
            return True, response.text

        return False, response.text

    except Exception as e:
        print("WHATSAPP SEND ERROR:", str(e))
        return False, str(e)


@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>WhatsApp API</title>
    </head>

    <body style="
        font-family: Arial, sans-serif;
        padding: 30px;
        background: #f5f5f5;
    ">

        <div style="
            max-width: 500px;
            margin: auto;
            background: white;
            padding: 25px;
            border-radius: 12px;
        ">

            <h2>WhatsApp API is Running ✅</h2>

            <p>
                Webhook server is active.
            </p>

            <a href="/dashboard">
                Open WhatsApp Inbox
            </a>

        </div>

    </body>
    </html>
    """


@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    # --------------------------------------------------
    # META WEBHOOK VERIFICATION
    # --------------------------------------------------

    if request.method == "GET":

        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("WEBHOOK VERIFIED")
            return challenge, 200

        return "Verification failed", 403

    # --------------------------------------------------
    # RECEIVE WHATSAPP MESSAGE
    # --------------------------------------------------

    data = request.get_json(silent=True) or {}

    print("WEBHOOK DATA:")
    print(data)

    try:

        entries = data.get("entry", [])

        for entry in entries:

            changes = entry.get("changes", [])

            for change in changes:

                value = change.get("value", {})

                contacts = value.get("contacts", [])
                incoming_messages = value.get("messages", [])

                for msg in incoming_messages:

                    phone = msg.get("from", "")
                    message_type = msg.get("type", "unknown")

                    # Customer name
                    name = phone

                    if contacts:
                        name = (
                            contacts[0]
                            .get("profile", {})
                            .get("name", phone)
                        )

                    # Incoming message content
                    text = ""

                    if message_type == "text":

                        text = (
                            msg
                            .get("text", {})
                            .get("body", "")
                        )

                    elif message_type == "image":
                        text = "📷 Image received"

                    elif message_type == "document":
                        text = "📄 Document received"

                    elif message_type == "audio":
                        text = "🎵 Audio received"

                    elif message_type == "video":
                        text = "🎥 Video received"

                    elif message_type == "sticker":
                        text = "Sticker received"

                    elif message_type == "location":
                        text = "📍 Location received"

                    else:
                        text = f"{message_type} message received"

                    # Save incoming message
                    messages.append({
                        "direction": "incoming",
                        "name": name,
                        "phone": phone,
                        "message": text,
                        "type": message_type,
                        "time": datetime.now().strftime(
                            "%d-%m-%Y %I:%M %p"
                        )
                    })

                    print(
                        "NEW MESSAGE:",
                        name,
                        phone,
                        text
                    )

                    # --------------------------------------------------
                    # AUTOMATIC REPLY
                    # --------------------------------------------------

                    auto_success, auto_response = send_whatsapp_message(
                        phone,
                        AUTO_REPLY_MESSAGE
                    )

                    if auto_success:

                        messages.append({
                            "direction": "outgoing",
                            "name": "Automatic Reply",
                            "phone": phone,
                            "message": AUTO_REPLY_MESSAGE,
                            "type": "text",
                            "time": datetime.now().strftime(
                                "%d-%m-%Y %I:%M %p"
                            )
                        })

                        print(
                            "AUTO REPLY SENT TO:",
                            phone
                        )

                    else:

                        print(
                            "AUTO REPLY FAILED:",
                            auto_response
                        )

    except Exception as e:

        print("WEBHOOK ERROR:", str(e))

    # Meta requires 200 response
    return "EVENT_RECEIVED", 200


@app.route("/send-message", methods=["POST"])
def send_message():
    """
    Manual reply from dashboard.
    """

    phone = request.form.get("phone", "").strip()
    text = request.form.get("message", "").strip()

    if not phone or not text:
        return redirect("/dashboard")

    success, api_response = send_whatsapp_message(
        phone,
        text
    )

    if success:

        messages.append({
            "direction": "outgoing",
            "name": "You",
            "phone": phone,
            "message": text,
            "type": "text",
            "time": datetime.now().strftime(
                "%d-%m-%Y %I:%M %p"
            )
        })

        return redirect("/dashboard")

    return f"""
    <h2>Message Send Failed</h2>

    <p>{api_response}</p>

    <p>
        <a href="/dashboard">
            Back to Dashboard
        </a>
    </p>
    """, 500


@app.route("/dashboard")
def dashboard():

    customers = {}

    # --------------------------------------------------
    # GROUP MESSAGES BY CUSTOMER
    # --------------------------------------------------

    for msg in messages:

        phone = msg["phone"]

        if phone not in customers:

            customers[phone] = {
                "name": msg["name"],
                "phone": phone,
                "messages": []
            }

        # Keep customer name from incoming message
        if msg["direction"] == "incoming":
            customers[phone]["name"] = msg["name"]

        customers[phone]["messages"].append(msg)

    customer_cards = ""

    # --------------------------------------------------
    # BUILD CHAT CARDS
    # --------------------------------------------------

    for phone, customer in reversed(
        list(customers.items())
    ):

        conversation_html = ""

        for msg in customer["messages"]:

            if msg["direction"] == "outgoing":
                bubble_class = "outgoing"
            else:
                bubble_class = "incoming"

            safe_message = (
                msg["message"]
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
            )

            conversation_html += f"""
            <div class="message-row {bubble_class}-row">

                <div class="bubble {bubble_class}">

                    <div class="message-text">
                        {safe_message}
                    </div>

                    <div class="message-time">
                        {msg['time']}
                    </div>

                </div>

            </div>
            """

        customer_cards += f"""
        <div class="chat-card">

            <div class="customer-header">

                <div class="avatar">
                    {customer['name'][:1].upper()}
                </div>

                <div class="customer-info">

                    <div class="customer-name">
                        {customer['name']}
                    </div>

                    <div class="customer-phone">
                        +{phone}
                    </div>

                </div>

            </div>


            <div class="conversation">

                {conversation_html}

            </div>


            <form
                method="POST"
                action="/send-message"
                class="reply-form"
            >

                <input
                    type="hidden"
                    name="phone"
                    value="{phone}"
                >

                <input
                    type="text"
                    name="message"
                    placeholder="Type a reply..."
                    autocomplete="off"
                    required
                >

                <button type="submit">
                    Send
                </button>

            </form>

        </div>
        """

    if not customer_cards:

        customer_cards = """
        <div class="empty-card">

            <div class="empty-icon">
                💬
            </div>

            <h3>No messages yet</h3>

            <p>
                Send a WhatsApp message to your business
                number to start testing.
            </p>

        </div>
        """

    total_messages = len(messages)

    total_customers = len(customers)

    # --------------------------------------------------
    # DASHBOARD HTML
    # --------------------------------------------------

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>WhatsApp Inbox</title>

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1"
        >

        <meta
            http-equiv="refresh"
            content="15"
        >

        <style>

            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                font-family:
                    Arial,
                    Helvetica,
                    sans-serif;
                background: #f1f5f9;
                color: #111827;
            }}

            .topbar {{
                background: #111827;
                color: white;
                padding: 18px;
            }}

            .topbar-inner {{
                max-width: 950px;
                margin: auto;
            }}

            .title {{
                font-size: 25px;
                font-weight: bold;
            }}

            .subtitle {{
                color: #d1d5db;
                margin-top: 4px;
                font-size: 13px;
            }}

            .status {{
                display: inline-block;
                margin-top: 12px;
                background: #dcfce7;
                color: #166534;
                padding: 7px 12px;
                border-radius: 20px;
                font-size: 13px;
                font-weight: bold;
            }}

            .container {{
                max-width: 950px;
                margin: auto;
                padding: 16px;
            }}

            .stats {{
                display: grid;
                grid-template-columns:
                    repeat(2, 1fr);
                gap: 10px;
                margin-bottom: 16px;
            }}

            .stat-card {{
                background: white;
                border-radius: 12px;
                padding: 14px;
                box-shadow:
                    0 2px 8px
                    rgba(0,0,0,0.05);
            }}

            .stat-value {{
                font-size: 25px;
                font-weight: bold;
            }}

            .stat-label {{
                font-size: 12px;
                color: #6b7280;
                margin-top: 3px;
            }}

            .chat-card {{
                background: white;
                border-radius: 15px;
                margin-bottom: 18px;
                overflow: hidden;
                box-shadow:
                    0 2px 12px
                    rgba(0,0,0,0.08);
            }}

            .customer-header {{
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 14px;
                background: white;
                border-bottom:
                    1px solid #e5e7eb;
            }}

            .avatar {{
                width: 42px;
                height: 42px;
                border-radius: 50%;
                background: #16a34a;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
                font-size: 18px;
            }}

            .customer-name {{
                font-weight: bold;
                font-size: 16px;
            }}

            .customer-phone {{
                margin-top: 3px;
                color: #6b7280;
                font-size: 12px;
            }}

            .conversation {{
                background: #efeae2;
                padding: 14px;
                min-height: 160px;
                max-height: 420px;
                overflow-y: auto;
            }}

            .message-row {{
                display: flex;
                margin-bottom: 9px;
            }}

            .incoming-row {{
                justify-content: flex-start;
            }}

            .outgoing-row {{
                justify-content: flex-end;
            }}

            .bubble {{
                max-width: 82%;
                padding: 9px 11px;
                border-radius: 9px;
                font-size: 14px;
                line-height: 1.4;
                box-shadow:
                    0 1px 2px
                    rgba(0,0,0,0.08);
            }}

            .incoming {{
                background: white;
            }}

            .outgoing {{
                background: #d9fdd3;
            }}

            .message-time {{
                text-align: right;
                margin-top: 5px;
                font-size: 9px;
                color: #6b7280;
            }}

            .reply-form {{
                display: flex;
                gap: 8px;
                padding: 11px;
                background: white;
                border-top:
                    1px solid #e5e7eb;
            }}

            .reply-form input {{
                flex: 1;
                min-width: 0;
                border:
                    1px solid #d1d5db;
                padding: 12px 14px;
                border-radius: 24px;
                font-size: 15px;
                outline: none;
            }}

            .reply-form input:focus {{
                border-color: #16a34a;
            }}

            .reply-form button {{
                border: none;
                background: #16a34a;
                color: white;
                padding: 10px 18px;
                border-radius: 24px;
                font-weight: bold;
                cursor: pointer;
            }}

            .empty-card {{
                background: white;
                border-radius: 14px;
                padding: 40px 20px;
                text-align: center;
            }}

            .empty-icon {{
                font-size: 45px;
            }}

            .empty-card h3 {{
                margin-bottom: 6px;
            }}

            .empty-card p {{
                color: #6b7280;
            }}


            @media (max-width: 600px) {{

                .topbar {{
                    padding: 16px;
                }}

                .title {{
                    font-size: 22px;
                }}

                .container {{
                    padding: 10px;
                }}

                .stats {{
                    gap: 8px;
                }}

                .stat-card {{
                    padding: 12px;
                }}

                .bubble {{
                    max-width: 88%;
                }}

                .reply-form button {{
                    padding:
                        10px 15px;
                }}

            }}

        </style>

    </head>


    <body>

        <div class="topbar">

            <div class="topbar-inner">

                <div class="title">
                    WhatsApp Inbox
                </div>

                <div class="subtitle">
                    Sizal HD Lenses
                </div>

                <div class="status">
                    ● Webhook Connected
                </div>

            </div>

        </div>


        <div class="container">

            <div class="stats">

                <div class="stat-card">

                    <div class="stat-value">
                        {total_customers}
                    </div>

                    <div class="stat-label">
                        Conversations
                    </div>

                </div>

                <div class="stat-card">

                    <div class="stat-value">
                        {total_messages}
                    </div>

                    <div class="stat-label">
                        Messages
                    </div>

                </div>

            </div>


            {customer_cards}

        </div>

    </body>

    </html>
    """


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
