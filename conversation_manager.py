"""
conversation_manager.py
-----------------------
Thread-safe, in-memory conversation history store.

Each conversation is identified by a unique channel key, typically the
combination of the sender's phone number and the WhatsApp Business
phone-number-ID that received the message.  This guarantees that
histories are never mixed across users or business numbers.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List


class ConversationManager:
    """Stores per-channel message histories for GPT context."""

    def __init__(self, max_history: int = 20) -> None:
        """
        Args:
            max_history: Maximum number of messages (user + assistant) to
                         retain per conversation.  Older messages are
                         evicted when the limit is reached.
        """
        if max_history < 1:
            raise ValueError("max_history must be at least 1")
        self._max_history = max_history
        self._histories: Dict[str, deque] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def make_channel_key(sender: str, phone_number_id: str) -> str:
        """Return a stable string key for a conversation channel.

        Args:
            sender: The sender's WhatsApp phone number (e.g. "14155550100").
            phone_number_id: The WhatsApp Business phone-number-ID.

        Returns:
            A colon-separated composite key.
        """
        return f"{sender}:{phone_number_id}"

    def add_message(self, channel_key: str, role: str, content: str) -> None:
        """Append a message to a conversation history.

        Args:
            channel_key: Identifier returned by :meth:`make_channel_key`.
            role: OpenAI role string — ``"user"`` or ``"assistant"``.
            content: The message text.
        """
        if role not in {"user", "assistant", "system"}:
            raise ValueError(f"Invalid role: {role!r}")
        with self._lock:
            if channel_key not in self._histories:
                self._histories[channel_key] = deque(maxlen=self._max_history)
            self._histories[channel_key].append({"role": role, "content": content})

    def get_history(self, channel_key: str) -> List[dict]:
        """Return a snapshot of the conversation history.

        Args:
            channel_key: Identifier returned by :meth:`make_channel_key`.

        Returns:
            A list of ``{"role": ..., "content": ...}`` dicts ordered
            oldest-first, safe to pass directly to the OpenAI API.
        """
        with self._lock:
            return list(self._histories.get(channel_key, []))

    def clear_history(self, channel_key: str) -> None:
        """Remove all history for a conversation channel.

        Args:
            channel_key: Identifier returned by :meth:`make_channel_key`.
        """
        with self._lock:
            self._histories.pop(channel_key, None)

    def channel_count(self) -> int:
        """Return the number of active conversation channels."""
        with self._lock:
            return len(self._histories)
