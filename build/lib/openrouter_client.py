"""Thin OpenRouter client (parity with cook_book openrouter_api)."""

from __future__ import annotations

import json
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_APP_TITLE = "phosphor-icons-semantic-search-mcp"


class OpenRouterApiError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        referer: str | None = None,
        app_title: str = DEFAULT_APP_TITLE,
    ) -> None:
        if not api_key:
            raise ValueError("OpenRouter API key must not be empty.")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-OpenRouter-Title": app_title,
        }

        if referer:
            headers["HTTP-Referer"] = referer

        self._client = httpx.Client(base_url=base_url, headers=headers, timeout=120.0)

    def close(self) -> None:
        self._client.close()

    def create_chat_completion_json(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        response_format: dict[str, str] | None = None,
        temperature: float | None = 0.2,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }

        if response_format is not None:
            payload["response_format"] = response_format

        if temperature is not None:
            payload["temperature"] = temperature

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        response_map = self._post_json("/chat/completions", payload)
        choices = response_map.get("choices", [])

        if not choices:
            raise OpenRouterApiError("Chat completion returned no choices.")

        first_choice = choices[0]
        choice_error = first_choice.get("error")

        if choice_error and choice_error.get("message"):
            raise OpenRouterApiError(
                choice_error["message"],
                details=choice_error,
            )

        message = first_choice.get("message", {})
        content = message.get("content")

        if not content:
            raise OpenRouterApiError("Chat completion did not include assistant content.")

        try:
            decoded = json.loads(content)
        except json.JSONDecodeError as error:
            raise OpenRouterApiError(
                "Failed to decode assistant JSON response.",
                details=error,
            ) from error

        if not isinstance(decoded, dict):
            raise OpenRouterApiError("Assistant response content was not a JSON object.")

        return decoded

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.post(path, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise self._map_http_error(error) from error
        except httpx.HTTPError as error:
            raise OpenRouterApiError(str(error) or "OpenRouter request failed.") from error

        data = response.json()

        if not isinstance(data, dict):
            raise OpenRouterApiError(
                f"Unexpected response payload type: {type(data).__name__}."
            )

        return data

    def _map_http_error(self, error: httpx.HTTPStatusError) -> OpenRouterApiError:
        status_code = error.response.status_code
        parsed: dict[str, Any] | None = None

        try:
            body = error.response.json()
            if isinstance(body, dict):
                parsed = body
        except json.JSONDecodeError:
            parsed = None

        if parsed is not None:
            root_error = parsed.get("error")
            if isinstance(root_error, dict) and root_error.get("message"):
                return OpenRouterApiError(
                    str(root_error["message"]),
                    status_code=status_code,
                    details=parsed,
                )

            message = parsed.get("message")
            if message is not None:
                return OpenRouterApiError(
                    str(message),
                    status_code=status_code,
                    details=parsed,
                )

        return OpenRouterApiError(
            str(error) or "OpenRouter request failed.",
            status_code=status_code,
            details=error.response.text,
        )
