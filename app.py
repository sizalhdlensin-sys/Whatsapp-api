from flask import Flask, request, jsonify
import os
from datetime import datetime

app = Flask(__name__)

VERIFY_TOKEN = "my_verify_token"

# Temporary message storage
messages = []


@app.route("/")
def home():
    return """
    <h2>WhatsApp API is Running ✅</h2>
    <p><a href="/dashboard">Open Message Dashboard</a></p>
    """


@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    # Meta webhook verification
    if request.method == "GET":

        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200

        return "Verification failed", 403

    # Receive WhatsApp messages
    if request.method == "POST":

        data = request.get_json(silent=True) or {}

        print(data)

        try:
            entry = data.get("entry", [])

            for item in entry:
                changes = item.get("changes", [])

                for change in changes:

                    value = change.get("value", {})

                    contacts = value.get("contacts", [])
                    incoming_messages = value.get("messages", [])

                    for msg in incoming_messages:

                        phone = msg.get("from", "Unknown")
                        message_type = msg.get("type", "unknown")

                        name = phone

                        if contacts:
                            profile = contacts[0].get("profile", {})
                            name = profile.get("name", phone)

                        text = ""

                        if message_type == "text":
                            text = msg.get("text", {}).get("body", "")

                        messages.append({
                            "name": name,
                            "phone": phone,
                            "message": text,
                            "type": message_type,
                            "time": datetime.now().strftime("%d-%m-%Y %I:%M %p")
                        })

                        print(
                            f"NEW MESSAGE: {name} | {phone} | {text}"
                        )

        except Exception as e:
            print("Webhook Error:", e)

        return "EVENT_RECEIVED", 200


@app.route("/api/messages")
def api_messages():
    return jsonify(messages)


@app.route("/dashboard")
def dashboard():

    rows = ""

    for msg in reversed(messages):

        rows += f"""
        <tr>
            <td>{msg['name']}</td>
            <td>{msg['phone']}</td>
            <td>{msg['message']}</td>
            <td>{msg['time']}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>

    <html>

    <head>

        <title>WhatsApp Dashboard</title>

        <meta name="viewport"
        content="width=device-width, initial-scale=1">

        <style>

            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                background: #f5f7fa;
            }}

            .header {{
                background: #111827;
                color: white;
                padding: 20px;
            }}

            .header h2 {{
                margin: 0;
            }}

            .container {{
                padding: 20px;
            }}

            .card {{
                background: white;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                overflow-x: auto;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
            }}

            th {{
                text-align: left;
                background: #f3f4f6;
                padding: 12px;
            }}

            td {{
                padding: 12px;
                border-bottom: 1px solid #eee;
            }}

            .status {{
                display: inline-block;
                background: #dcfce7;
                color: #166534;
                padding: 6px 12px;
                border-radius: 20px;
                margin-top: 10px;
            }}

        </style>

    </head>


    <body>

        <div class="header">

            <h2>WhatsApp Message Dashboard</h2>

            <div class="status">
                ● Webhook Connected
            </div>

        </div>


        <div class="container">

            <div class="card">

                <h3>Incoming Messages</h3>

                <table>

                    <tr>
                        <th>Name</th>
                        <th>WhatsApp Number</th>
                        <th>Message</th>
                        <th>Time</th>
                    </tr>

                    {rows}

                </table>

            </div>

        </div>

    </body>

    </html>
    """


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
