# WhatsApp Business Listener Skill

Receive incoming WhatsApp messages via webhook notifications and respond automatically using OpenAI GPT — with full conversation-channel separation.

---

## Features

- 📨 **Webhook listener** — processes incoming WhatsApp Business messages
- 🤖 **GPT integration** — generates context-aware replies via OpenAI Chat Completions
- 🔀 **Channel separation** — keeps conversation histories isolated per user/phone number
- 🛡️ **Signature validation** — verifies `X-Hub-Signature-256` on every request
- 📱 **Android-ready** — includes a Kotlin sample for Android 15+ (API 35+)

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | Backend runtime |
| A [Meta Developer App](https://developers.facebook.com/) | WhatsApp Business Cloud API access |
| An [OpenAI API Key](https://platform.openai.com/api-keys) | GPT model access |
| A publicly reachable HTTPS URL | Required by Meta for webhooks (use [ngrok](https://ngrok.com/) during development) |

---

## Quick Start

### 1 — Clone and install dependencies

```bash
git clone https://github.com/aure576/WhatsApp12.git
cd WhatsApp12
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2 — Configure environment variables

```bash
cp config.template.env .env
# Edit .env and fill in your keys
```

Required variables:

| Variable | Description |
|---|---|
| `WHATSAPP_API_TOKEN` | Bearer token from Meta App Dashboard |
| `WHATSAPP_PHONE_NUMBER_ID` | Numeric phone-number-ID from Meta |
| `WHATSAPP_VERIFY_TOKEN` | Token you set in Meta Webhooks config |
| `WHATSAPP_APP_SECRET` | Meta App Secret (for signature validation) |
| `OPENAI_API_KEY` | Your OpenAI API key |

### 3 — Run the development server

Create a minimal Flask app (`app.py`) or use the example below:

```python
import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from webhook_listener import WebhookListener
from conversation_manager import ConversationManager
from gpt_responder import GPTResponder
from whatsapp_sender import WhatsAppSender

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

app = Flask(__name__)

manager  = ConversationManager(max_history=int(os.getenv("MAX_HISTORY", 20)))
responder = GPTResponder(
    api_key=os.environ["OPENAI_API_KEY"],
    model=os.getenv("GPT_MODEL", "gpt-4o-mini"),
    system_prompt=os.getenv("SYSTEM_PROMPT", "You are a helpful assistant."),
)
sender = WhatsAppSender(
    api_token=os.environ["WHATSAPP_API_TOKEN"],
    phone_number_id=os.environ["WHATSAPP_PHONE_NUMBER_ID"],
)
listener = WebhookListener(
    conversation_manager=manager,
    gpt_responder=responder,
    whatsapp_sender=sender,
    verify_token=os.getenv("WHATSAPP_VERIFY_TOKEN"),
    app_secret=os.getenv("WHATSAPP_APP_SECRET"),
)

@app.get("/webhook")
def verify():
    challenge = listener.verify_subscription(request.args.to_dict())
    if challenge:
        return challenge, 200
    return "Forbidden", 403

@app.post("/webhook")
def handle():
    result = listener.handle(request.get_json(force=True))
    return jsonify(result), 200

if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", 8080)))
```

```bash
python app.py
```

### 4 — Expose your server with ngrok (development only)

```bash
ngrok http 8080
```

Copy the `https://...ngrok-free.app` URL and configure it in your **Meta App Dashboard → WhatsApp → Configuration → Webhook URL** with the path `/webhook`.

### 5 — Configure Meta webhooks

1. Go to [Meta App Dashboard](https://developers.facebook.com/) → your app → **WhatsApp → Configuration**.
2. Set **Callback URL** to `https://<your-ngrok-url>/webhook`.
3. Set **Verify Token** to the value of `WHATSAPP_VERIFY_TOKEN` in your `.env`.
4. Subscribe to the **messages** field.

---

## Project Structure

```
WhatsApp12/
├── webhook_listener.py      # Parses webhook payloads, orchestrates pipeline
├── gpt_responder.py         # OpenAI GPT integration
├── whatsapp_sender.py       # WhatsApp Business Cloud API client
├── conversation_manager.py  # Thread-safe per-channel conversation history
├── android_example.kt       # Kotlin sample for Android 16+ (API 35+)
├── config.template.env      # Environment variable template
├── requirements.txt         # Python dependencies
├── SKILL.md                 # Skill interface documentation
└── README.md                # This file
```

---

## Android Integration

See [`android_example.kt`](android_example.kt) for a complete Kotlin example.

**Minimum SDK**: 35 (Android 15)

The example demonstrates:
- Constructing a simulated webhook payload on the device
- Posting it to the Python backend via Retrofit
- Displaying the GPT reply in a `RecyclerView`
- Storing the backend URL securely with `EncryptedSharedPreferences`

Add these dependencies to `app/build.gradle.kts`:

```kotlin
implementation("com.squareup.retrofit2:retrofit:2.11.0")
implementation("com.squareup.retrofit2:converter-gson:2.11.0")
implementation("androidx.security:security-crypto:1.1.0-alpha06")
implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.0")
implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.0")
```

---

## Security

- **Never** commit your `.env` file — it is in `.gitignore` by default.
- Store credentials on Android using `EncryptedSharedPreferences`, never in source code.
- Enable `X-Hub-Signature-256` validation in production by setting `WHATSAPP_APP_SECRET`.
- Use HTTPS for all API calls.

---

## License

MIT — see [LICENSE](LICENSE) for details.
