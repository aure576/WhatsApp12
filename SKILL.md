# WhatsApp Business Listener Skill

A skill that receives incoming WhatsApp messages via webhook notifications and responds coherently using GPT integration.

## Overview

This skill provides an automated WhatsApp Business messaging pipeline:
1. Listens for incoming messages via webhook
2. Maintains per-conversation context to prevent mixing channels
3. Generates intelligent, context-aware replies using OpenAI GPT
4. Sends the reply back through the WhatsApp Business API

## Interface

### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `webhook_payload` | JSON | Yes | Raw webhook notification body from WhatsApp Business API |
| `openai_api_key` | string | Yes | OpenAI API key for GPT access |
| `whatsapp_api_token` | string | Yes | WhatsApp Business API bearer token |
| `whatsapp_phone_number_id` | string | Yes | WhatsApp Business phone number ID |
| `gpt_model` | string | No | GPT model to use (default: `gpt-4o-mini`) |
| `system_prompt` | string | No | Custom system prompt for GPT (default: helpful assistant) |
| `max_history` | integer | No | Maximum messages kept per conversation (default: 20) |

### Outputs

| Parameter | Type | Description |
|-----------|------|-------------|
| `response_text` | string | The GPT-generated reply that was sent |
| `conversation_id` | string | Identifier of the conversation channel |
| `message_sid` | string | WhatsApp message ID of the sent reply |
| `status` | string | `success` or `error` |
| `error` | string | Error message if `status` is `error` |

## Usage Example

```python
from webhook_listener import WebhookListener
from conversation_manager import ConversationManager
from gpt_responder import GPTResponder
from whatsapp_sender import WhatsAppSender

# Initialise components
manager  = ConversationManager(max_history=20)
responder = GPTResponder(api_key="sk-...", model="gpt-4o-mini")
sender   = WhatsAppSender(api_token="EAA...", phone_number_id="12345678")

listener = WebhookListener(
    conversation_manager=manager,
    gpt_responder=responder,
    whatsapp_sender=sender,
)

# In your web-framework route handler:
result = listener.handle(webhook_payload)
print(result["response_text"])
```

## Webhook Verification

WhatsApp requires a one-time GET request verification. Mount the verify endpoint at the same URL:

```
GET /webhook?hub.mode=subscribe&hub.verify_token=<TOKEN>&hub.challenge=<CHALLENGE>
```

Set `WHATSAPP_VERIFY_TOKEN` in your environment to validate the token.

## Channel Separation

Every unique `(sender_phone, recipient_phone_number_id)` pair is treated as an isolated conversation. The `ConversationManager` stores message history keyed by this pair so that replies are always coherent within a single thread and never bleed across users or groups.

## Android Integration

See [`android_example.kt`](android_example.kt) for a complete Kotlin example that:
- Starts a local HTTP server on the device to receive forwarded webhooks
- Calls the Python backend (or a REST wrapper) to process the message
- Displays the GPT reply in a `RecyclerView`

Minimum Android API level: **35 (Android 15)**.

## Security Notes

- Store all API keys in environment variables or Android `EncryptedSharedPreferences` — never hard-code them.
- Validate the `X-Hub-Signature-256` header on every incoming webhook request.
- Use HTTPS for all outbound API calls.

## Files

| File | Purpose |
|------|---------|
| `webhook_listener.py` | Entry point — parses webhook payload and orchestrates the pipeline |
| `gpt_responder.py` | Calls OpenAI Chat Completions API |
| `whatsapp_sender.py` | Calls WhatsApp Business Cloud API to send messages |
| `conversation_manager.py` | Thread-safe in-memory conversation history |
| `config.template.env` | Template for required environment variables |
| `android_example.kt` | Kotlin sample for Android 16+ |
| `requirements.txt` | Python dependencies |
| `README.md` | Setup and deployment guide |
