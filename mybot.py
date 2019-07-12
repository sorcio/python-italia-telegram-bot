import json

import trio

from tgtrio import TelegramBotApi, Dispatcher, command_handler, load_settings, fetch_loop


async def play_bot(tg: TelegramBotApi, dispatcher: Dispatcher) -> None:
    from typing import List, Callable
    from tgtrio.flood_control import flood_control

    consumers: List[Callable] = [update_dumper, command_handler.consumer, flood_control]
    async with trio.open_nursery() as nursery:
        for c in consumers:
            nursery.start_soon(c, tg, dispatcher)


async def update_dumper(tg: TelegramBotApi, dispatcher: Dispatcher) -> None:
    async with dispatcher.consume() as consumer:
        async for item in consumer:
            print("* new update *")
            print(json.dumps(item, indent=2))


@command_handler.register("/help")
async def handle_help(tg: TelegramBotApi, command: str, message: dict) -> None:
    help_message = {
        "chat_id": message["chat"]["id"],
        "parse_mode": "Markdown",
        "text": """I'm just a testing bot but I'm willing to help""",
    }
    await tg.sendMessage(help_message)


async def amain() -> None:
    settings = load_settings()
    tg = TelegramBotApi.from_settings(settings)
    dispatcher = Dispatcher[dict]()
    try:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(fetch_loop, tg, dispatcher)
            nursery.start_soon(dispatcher.run)
            await play_bot(tg, dispatcher)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    trio.run(amain)
