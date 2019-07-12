from os import PathLike
from typing import Any, Mapping, List, Union

import toml


class MappingWrapper:
    __slots__ = ("_mapping", "_path")

    def __init__(self, mapping: Mapping[str, Any], path: List[str] = []):
        self._mapping = mapping
        self._path = path

    def _get_path(self):
        return ".".join(self._path)

    def __getattr__(self, key: str) -> Any:
        try:
            value = self[key]
        except KeyError as exc:
            raise AttributeError(
                f"{type(self).__name__} has no attribute"
                f" at path {self._get_path()}.{key!r}"
            )
        setattr(self, key, value)
        return value

    def __getitem__(self, key: str) -> Any:
        value = self._mapping[key]
        if isinstance(value, Mapping):
            value = type(self)(value, self._path + [key])
        return value

    def __repr__(self):
        if self._path:
            path_part = f".{self._get_path()}"
        else:
            path_part = ""
        return f"{type(self).__name__}{path_part}({self._mapping!r})"


class Settings(MappingWrapper):
    pass


def load_settings(path: Union[str, PathLike] = "tgbot.toml") -> Settings:
    with open(path) as f:
        settings = toml.load(f)
    return Settings(settings)


__all__ = [
    "load_settings",
    "Settings",
]
