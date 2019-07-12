import asks
asks.init("trio")

from ._settings import *
from ._loop import *
from ._tgapi import *
from ._commands import command_handler


__all__ = [
    "load_settings",
    "Dispatcher",
    "TelegramBotApi",
    "command_handler",
]

def main():
    pass


# from datetime import datetime
# from functools import partial
# from itertools import count
# import json
# from pathlib import Path

# import trio





