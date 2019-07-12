from itertools import count
from pathlib import Path
from typing import Dict, Generic, Optional, TypeVar

from async_generator import asynccontextmanager
import trio

from ._tgapi import TelegramBotApi


T = TypeVar("T")


class Dispatcher(Generic[T]):
    def __init__(self, max_size: int = 0):
        self.inlet, self._inlet_recv = trio.open_memory_channel[T](max_size)
        self._outlets: Dict[int, trio.abc.SendChannel[T]] = {}
        self._counter = count()

    @asynccontextmanager
    async def consume(self, max_size: int = 0):
        outlet_id = next(self._counter)
        send_channel, recv_channel = trio.open_memory_channel[T](max_size)
        self._outlets[outlet_id] = send_channel
        async with recv_channel:
            try:
                yield recv_channel
            finally:
                del self._outlets[outlet_id]

    async def run(self) -> None:
        async with self._inlet_recv:
            async for item in self._inlet_recv:
                async with trio.open_nursery() as nursery:
                    for outlet in self._outlets.values():
                        nursery.start_soon(self._send_item, outlet, item)

    async def _send_item(self, outlet: trio.abc.SendChannel[T], item: T):
        try:
            await outlet.send(item)
        except trio.ClosedResourceError:
            pass


def get_last_update_id(*, path="last_update_id") -> Optional[int]:
    try:
        last_update_id = int(Path(path).read_text("ascii").strip())
    except IOError:
        return None
    except ValueError:
        return None
    else:
        return last_update_id


def set_last_update_id(value: int, *, path="last_update_id") -> None:
    Path(path).write_text(str(value), "ascii")


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
                if last_update_id:
                    set_last_update_id(last_update_id)


__all__ = [
    "Dispatcher",
    "fetch_loop",
]
