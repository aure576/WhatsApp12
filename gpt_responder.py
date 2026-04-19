"""
gpt_responder.py
----------------
Generates intelligent, context-aware responses using the OpenAI
Chat Completions API (GPT).

The caller is responsible for providing the conversation history; this
module is intentionally stateless so that it can be reused across
multiple concurrent requests.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import openai

logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, friendly, and concise assistant communicating "
    "through WhatsApp. Keep your answers brief and clear."
)

_DEFAULT_MODEL = "gpt-4o-mini"


class GPTResponder:
    """Wraps the OpenAI Chat Completions API."""

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        system_prompt: str = _DEFAULT_SYSTEM_PROMPT,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> None:
        """
        Args:
            api_key: OpenAI API key (``sk-...``).
            model: Chat model identifier, e.g. ``"gpt-4o-mini"`` or
                   ``"gpt-4o"``.
            system_prompt: Instruction injected as the ``system`` role at
                           the start of every conversation.
            temperature: Sampling temperature (0 = deterministic).
            max_tokens: Maximum tokens in the completion.
        """
        if not api_key:
            raise ValueError("api_key must not be empty")
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model
        self._system_prompt = system_prompt
        self._temperature = temperature
        self._max_tokens = max_tokens

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_response(
        self,
        user_message: str,
        history: Optional[List[dict]] = None,
    ) -> str:
        """Call the OpenAI API and return the assistant reply.

        Args:
            user_message: The latest message from the WhatsApp user.
            history: Previous ``{"role": ..., "content": ...}`` messages
                     for this conversation channel, oldest-first.  Pass
                     ``None`` or an empty list for a fresh conversation.

        Returns:
            The text content of the GPT reply.

        Raises:
            openai.OpenAIError: On any API-level error (network, quota,
                                invalid key, etc.).
        """
        messages = [{"role": "system", "content": self._system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        logger.debug(
            "Calling OpenAI model=%s with %d messages", self._model, len(messages)
        )

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )

        reply = response.choices[0].message.content or ""
        logger.debug("OpenAI reply: %s", reply[:120])
        return reply
