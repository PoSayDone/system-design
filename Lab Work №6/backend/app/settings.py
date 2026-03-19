from __future__ import annotations

import os
from pathlib import Path


class SingletonMeta(type):
    _instances: dict[type, object] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Settings(metaclass=SingletonMeta):
    def __init__(self) -> None:
        default_path = Path(__file__).with_name("lab6.sqlite3")
        self.db_path = Path(os.getenv("LAB6_DB_PATH", str(default_path)))
