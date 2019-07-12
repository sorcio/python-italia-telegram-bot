from functools import partial
from typing import Any, Callable, Mapping

import asks

from ._settings import Settings


class TelegramApiBaseError(Exception):
    pass


class TelegramApiHttpError(TelegramApiBaseError):
    pass


class TelegramApiSerializationError(TelegramApiBaseError):
    pass


class TelegramApiError(TelegramApiBaseError):
    def __init__(self, message: str, http_code: int, error_code: int, parameters: list):
        super().__init__(message)
        self.http_code = http_code
        self.error_code = error_code
        self.parameters = parameters

    def __str__(self):
        return (
            "TelegramApiError("
            f"{self.message}, "
            f"http_code={self.http_code}, "
            f"error_code={self.error_code})"
        )


class TelegramBotApi:
    def __init__(self, token: str):
        self._token = token

    async def do_post(self, method: str, params: Mapping[str, Any] = None) -> dict:
        url = self._tg_url(method)
        try:
            r = await asks.post(url, data=params)
        except asks.error.AsksException as exc:
            raise TelegramApiHttpError from exc
        http_ok = r.status_code in range(200, 300)
        try:
            response = r.json()
        except ValueError:
            if http_ok:
                raise TelegramApiSerializationError from None
        is_ok = response.get("ok", False)
        if not is_ok:
            error_description = response.get("description", "server error")
            error_code = response.get("error_code", None)
            error_parameters = response.get("parameters", None)
            raise TelegramApiError(
                error_description, r.status_code, error_code, error_parameters
            )
        try:
            return response["result"]
        except KeyError:
            raise TelegramApiSerializationError(
                "response is missing 'result'"
            ) from None

    def __getattr__(self, key: str) -> Callable:
        return partial(self.do_post, key)

    def _tg_url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self._token}/{method}"

    @classmethod
    def from_settings(cls, settings: Settings):
        token: str = settings.tgtrio.api.token
        return cls(token=token)


def get_entity_text(message: dict, entity: dict) -> str:
    text = message.get("text", "")
    start = entity["offset"]
    end = start + entity["length"]
    return text[start:end]


def get_user_display_name(user: dict) -> str:
    try:
        return f"@{user['username']}"
    except KeyError:
        return f"{user['first_name']}"


__all__ = [
    "TelegramApiBaseError",
    "TelegramApiError",
    "TelegramApiSerializationError",
    "TelegramApiHttpError",
    "TelegramBotApi",
    "get_entity_text",
    "get_user_display_name",
]
