import logging
from typing import Any, Callable, Coroutine, Dict

from ._loop import Dispatcher
from ._tgapi import TelegramBotApi, get_entity_text


logger = logging.getLogger(__name__)

Handler = Callable[[TelegramBotApi, str, dict], Coroutine[Any, Any, None]]


class CommandHandler:
    def __init__(self):
        self._handlers: Dict[str, Handler] = {}

    async def consumer(self, tg: TelegramBotApi, dispatcher: Dispatcher) -> None:
        async with dispatcher.consume() as consumer:
            async for item in consumer:
                try:
                    await self._handle_update(tg, item)
                except Exception as exc:
                    logger.exception("unhandled exception in CommandHandler")

    async def _handle_update(self, tg: TelegramBotApi, update: dict) -> Any:
        if "message" in update:
            return await self._handle_message(tg, update["message"])

    async def _handle_message(self, tg: TelegramBotApi, message: dict) -> None:
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

    def register(self, command: str) -> Callable[[Handler], Handler]:
        if not command.startswith("/"):
            raise ValueError("command must start with '/'")

        def decorator(func: Handler) -> Handler:
            self._handlers[command] = func
            return func

        return decorator


command_handler = CommandHandler()
