"""
whatsapp_sender.py
------------------
Sends text messages via the WhatsApp Business Cloud API.

Docs: https://developers.facebook.com/docs/whatsapp/cloud-api/messages/text-messages
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

_CLOUD_API_URL = (
    "https://graph.facebook.com/v19.0/{phone_number_id}/messages"
)


class WhatsAppSender:
    """Thin wrapper around the WhatsApp Business Cloud API send endpoint."""

    def __init__(self, api_token: str, phone_number_id: str) -> None:
        """
        Args:
            api_token: WhatsApp Business API bearer token (``EAA...``).
            phone_number_id: The numeric ID of the WhatsApp Business
                             phone number that will send replies.
        """
        if not api_token:
            raise ValueError("api_token must not be empty")
        if not phone_number_id:
            raise ValueError("phone_number_id must not be empty")
        self._token = api_token
        self._phone_number_id = phone_number_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_text(self, to: str, text: str) -> dict:
        """Send a plain-text WhatsApp message.

        Args:
            to: Recipient phone number in E.164 format (e.g.
                ``"14155550100"``), without the leading ``+``.
            text: Message body text.

        Returns:
            Parsed JSON response from the WhatsApp API.

        Raises:
            requests.HTTPError: If the API returns a non-2xx status.
        """
        url = _CLOUD_API_URL.format(phone_number_id=self._phone_number_id)
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }

        logger.debug("Sending WhatsApp text message")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        logger.debug("WhatsApp API responded with status %d", response.status_code)
        return data

    def mark_as_read(self, message_id: str) -> dict:
        """Mark an incoming message as read (shows double blue tick).

        Args:
            message_id: The ``wamid`` of the received message.

        Returns:
            Parsed JSON response from the WhatsApp API.

        Raises:
            requests.HTTPError: If the API returns a non-2xx status.
        """
        url = _CLOUD_API_URL.format(phone_number_id=self._phone_number_id)
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
