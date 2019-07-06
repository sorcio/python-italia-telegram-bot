from collections import defaultdict
from datetime import datetime
from typing import Mapping, NewType, Tuple

from . import TelegramBotApi, Dispatcher, get_user_display_name
from .activity_monitor import ActivityMonitor


ChatId = NewType("ChatId", str)
UserId = NewType("UserId", str)
MonitorKey = Tuple[ChatId, UserId]
MonitorMapping = Mapping[MonitorKey, ActivityMonitor]


async def flood_control(tg: TelegramBotApi, dispatcher: Dispatcher, threshold=0.5):
    monitors: MonitorMapping = defaultdict(lambda: ActivityMonitor(period=5.0))
    async with dispatcher.consume() as consumer:
        async for item in consumer:
            if "message" in item:
                chat_id: ChatId = item["message"]["chat"]["id"]
                from_id: UserId = item["message"]["from"]["id"]
                timestamp = datetime.fromtimestamp(item["message"]["date"])
                monitor_id = (chat_id, from_id)
                monitor = monitors[monitor_id]
                alerting = monitor.update_activity(timestamp)
                if alerting:
                    user_display = get_user_display_name(item["message"]["from"])
                    await tg.sendMessage(
                        {
                            "chat_id": chat_id,
                            "parse_mode": "Markdown",
                            "text": f"Hey [{user_display}](tg://user?id={from_id}), you might be writing too fast!",
                        }
                    )
                chat_name = item["message"]["chat"].get("title") or "private"
                user_name = item["message"]["from"]["username"]
                print(f"freq: [{chat_name}][{user_name}] {monitor.last_frequency:.2f})")
