"""
webhook_listener.py
-------------------
Entry point for the WhatsApp Business webhook pipeline.

Responsibilities:
- Parse the incoming webhook payload (POST body sent by Meta).
- Verify the webhook subscription challenge (GET request from Meta).
- Orchestrate: extract message → fetch history → call GPT → send reply.

This module is framework-agnostic.  Wire it into Flask, FastAPI, Django,
or any WSGI/ASGI framework by calling the appropriate public methods from
your route handlers.

Webhook payload format reference:
https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

from conversation_manager import ConversationManager
from gpt_responder import GPTResponder
from whatsapp_sender import WhatsAppSender

logger = logging.getLogger(__name__)


class WebhookListener:
    """Orchestrates the full incoming-message pipeline."""

    def __init__(
        self,
        conversation_manager: ConversationManager,
        gpt_responder: GPTResponder,
        whatsapp_sender: WhatsAppSender,
        verify_token: Optional[str] = None,
        app_secret: Optional[str] = None,
    ) -> None:
        """
        Args:
            conversation_manager: Stores per-channel message histories.
            gpt_responder: Generates GPT replies.
            whatsapp_sender: Sends messages back via WhatsApp.
            verify_token: Token used to verify the webhook subscription
                          (set in your Meta App Dashboard and in
                          ``WHATSAPP_VERIFY_TOKEN`` env var).
            app_secret: Meta App Secret used to validate
                        ``X-Hub-Signature-256`` request signatures.
                        Strongly recommended in production.
        """
        self._manager = conversation_manager
        self._responder = gpt_responder
        self._sender = whatsapp_sender
        self._verify_token = verify_token
        self._app_secret = app_secret

    # ------------------------------------------------------------------
    # Webhook verification (GET)
    # ------------------------------------------------------------------

    def verify_subscription(self, params: Dict[str, str]) -> Optional[str]:
        """Handle Meta's webhook subscription verification challenge.

        Call this from your GET /webhook route handler.

        Args:
            params: Query parameters from the GET request
                    (``hub.mode``, ``hub.verify_token``, ``hub.challenge``).

        Returns:
            The ``hub.challenge`` string if verification succeeds,
            or ``None`` if it fails.
        """
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge")

        if mode == "subscribe" and token == self._verify_token:
            logger.info("Webhook subscription verified successfully.")
            return challenge

        logger.warning(
            "Webhook verification failed: mode=%r token_match=%s",
            mode,
            token == self._verify_token,
        )
        return None

    # ------------------------------------------------------------------
    # Signature validation
    # ------------------------------------------------------------------

    def validate_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """Verify the ``X-Hub-Signature-256`` HMAC signature.

        Args:
            raw_body: The raw bytes of the POST request body.
            signature_header: Value of the ``X-Hub-Signature-256`` header.

        Returns:
            ``True`` if the signature is valid or if no app secret is
            configured (development mode).  ``False`` otherwise.
        """
        if not self._app_secret:
            return True

        expected_prefix = "sha256="
        if not signature_header.startswith(expected_prefix):
            return False

        received_hash = signature_header[len(expected_prefix):]
        expected_hash = hmac.new(
            self._app_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(received_hash, expected_hash)

    # ------------------------------------------------------------------
    # Message processing (POST)
    # ------------------------------------------------------------------

    def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single incoming webhook notification.

        Call this from your POST /webhook route handler after you have
        parsed the JSON body.

        Args:
            payload: Parsed JSON dict from the WhatsApp webhook POST body.

        Returns:
            A result dict with keys:

            - ``status``: ``"success"``, ``"ignored"``, or ``"error"``
            - ``response_text``: The GPT reply that was sent (on success)
            - ``conversation_id``: Channel key (on success)
            - ``message_sid``: WhatsApp message ID of the sent reply
            - ``error``: Error message (on error)
        """
        try:
            message, phone_number_id = self._extract_message(payload)
        except _NotATextMessage:
            return {"status": "ignored", "reason": "not a text message"}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to extract message from payload")
            return {"status": "error", "error": str(exc)}

        sender = message["from"]
        text = message["text"]["body"]
        wamid = message["id"]
        channel_key = ConversationManager.make_channel_key(sender, phone_number_id)

        logger.info("Incoming text message received on channel (redacted)")

        # Mark as read (best-effort; do not fail the pipeline if this errors)
        try:
            self._sender.mark_as_read(wamid)
        except Exception:  # noqa: BLE001
            logger.warning("Could not mark incoming message as read")

        # Fetch history, add the new user message, then generate a reply
        history = self._manager.get_history(channel_key)
        self._manager.add_message(channel_key, "user", text)

        try:
            reply = self._responder.generate_response(text, history)
        except Exception as exc:  # noqa: BLE001
            logger.exception("GPT error for current channel")
            return {"status": "error", "error": str(exc)}

        self._manager.add_message(channel_key, "assistant", reply)

        try:
            send_result = self._sender.send_text(sender, reply)
        except Exception as exc:  # noqa: BLE001
            logger.exception("WhatsApp send error for current channel")
            return {"status": "error", "error": str(exc)}

        message_sid = (
            send_result.get("messages", [{}])[0].get("id", "")
        )
        return {
            "status": "success",
            "response_text": reply,
            "conversation_id": channel_key,
            "message_sid": message_sid,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_message(payload: Dict[str, Any]):
        """Extract the first text message from a webhook payload.

        Returns:
            A tuple of ``(message_dict, phone_number_id)``.

        Raises:
            _NotATextMessage: If the payload contains no text messages.
            KeyError: If the payload structure is unexpected.
        """
        entry = payload["entry"][0]
        change = entry["changes"][0]
        value = change["value"]
        phone_number_id = value["metadata"]["phone_number_id"]
        messages = value.get("messages", [])

        if not messages:
            raise _NotATextMessage("no messages in payload")

        message = messages[0]
        if message.get("type") != "text":
            raise _NotATextMessage(f"message type is {message.get('type')!r}")

        return message, phone_number_id


class _NotATextMessage(Exception):
    """Raised when the webhook payload does not contain a text message."""
