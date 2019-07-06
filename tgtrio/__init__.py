from datetime import datetime
from functools import partial
from itertools import count
import json
from pathlib import Path

import asks
from async_generator import asynccontextmanager
import trio


asks.init("trio")


class Dispatcher:
    def __init__(self, max_size=0):
        self.inlet, self._inlet_recv = trio.open_memory_channel(max_size)
        self._outlets = {}
        self._counter = count()

    @asynccontextmanager
    async def consume(self, max_size=0):
        outlet_id = next(self._counter)
        send_channel, recv_channel = trio.open_memory_channel(max_size)
        self._outlets[outlet_id] = send_channel
        async with recv_channel:
            try:
                yield recv_channel
            finally:
                del self._outlets[outlet_id]

    async def run(self):
        async with self._inlet_recv:
            async for item in self._inlet_recv:
                async with trio.open_nursery() as nursery:
                    for outlet in self._outlets.values():
                        nursery.start_soon(self._send_item, outlet, item)

    async def _send_item(self, outlet, item):
        try:
            await outlet.send(item)
        except trio.ClosedResourceError:
            pass


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

    async def do_post(self, method, params=None):
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

    def __getattr__(self, key):
        return partial(self.do_post, key)

    def _tg_url(self, method: str):
        return f"https://api.telegram.org/bot{self._token}/{method}"

    @staticmethod
    def _load_token(*, path: str):
        return Path(path).read_text("ascii").strip()

    @classmethod
    def from_token_file(cls, *, path: str = "tgtoken"):
        token = cls._load_token(path=path)
        return cls(token=token)


def get_last_update_id(*, path="last_update_id"):
    try:
        last_update_id = int(Path(path).read_text("ascii").strip())
    except IOError:
        return None
    except ValueError:
        return None
    else:
        return last_update_id


def set_last_update_id(value, *, path="last_update_id"):
    Path(path).write_text(str(value), "ascii")


def get_entity_text(message, entity):
    text = message.get("text", "")
    start = entity["offset"]
    end = start + entity["length"]
    return text[start:end]


def get_user_display_name(user):
    try:
        return f"@{user['username']}"
    except KeyError:
        return f"{user['first_name']}"


async def fetch_loop(tg: TelegramBotApi, dispatcher: Dispatcher):
    last_update_id = get_last_update_id()
    async with dispatcher.inlet:
        while True:
            params = {"timeout": 60}
            if last_update_id:
                params["offset"] = last_update_id + 1
            updates = await tg.getUpdates(params)
            for update in updates:
                await dispatcher.inlet.send(update)
                last_update_id = update["update_id"]
                set_last_update_id(last_update_id)


async def play_bot(tg: TelegramBotApi, dispatcher: Dispatcher):
    from .flood_control import flood_control

    consumers = [update_dumper, command_handler.consumer, flood_control]
    async with trio.open_nursery() as nursery:
        for c in consumers:
            nursery.start_soon(c, tg, dispatcher)


async def update_dumper(tg: TelegramBotApi, dispatcher: Dispatcher):
    async with dispatcher.consume() as consumer:
        async for item in consumer:
            print("* new update *")
            print(json.dumps(item, indent=2))


class CommandHandler:
    def __init__(self):
        self._handlers = {}

    async def consumer(self, tg: TelegramBotApi, dispatcher: Dispatcher):
        async with dispatcher.consume() as consumer:
            async for item in consumer:
                if "message" in item:
                    message = item["message"]
                    entities = message.get("entities", [])
                    for entity in entities:
                        if entity["type"] == "bot_command":
                            command = get_entity_text(message, entity)
                            try:
                                handler = self._handlers[command]
                            except KeyError:
                                pass
                            else:
                                try:
                                    await handler(tg, command, message)
                                except Exception as exc:
                                    print("exception in command handler:", exc)
                            break

    def register(self, command: str):
        if not command.startswith("/"):
            raise ValueError("command must start with '/'")

        def decorator(func):
            self._handlers[command] = func

        return decorator


command_handler = CommandHandler()


@command_handler.register("/help")
async def handle_help(tg: TelegramBotApi, command: str, message: dict):
    help_message = {
        "chat_id": message["chat"]["id"],
        "parse_mode": "Markdown",
        "text": """I'm just a testing bot but I'm willing to help""",
    }
    await tg.sendMessage(help_message)


async def amain():
    tg = TelegramBotApi.from_token_file()
    dispatcher = Dispatcher()
    try:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(fetch_loop, tg, dispatcher)
            nursery.start_soon(dispatcher.run)
            await play_bot(tg, dispatcher)
    except KeyboardInterrupt:
        pass
