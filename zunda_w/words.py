import os.path
from pathlib import Path
from typing import Set


class WordFilter:
    def __init__(self, config_path: str):
        self.data: Set[str] = self.read(config_path)

    @classmethod
    def read(cls, config_path: str) -> Set[str]:
        if not os.path.exists(config_path):
            return set()
        return set(
            map(str.strip, Path(config_path).read_text(encoding="UTF-8").splitlines())
        )

    def is_exclude(self, word: str) -> bool:
        return word not in self.data
