import os.path
import re
from pathlib import Path
from typing import Set, Tuple


class WordFilter:
    def __init__(self, config_path: str):
        self.data, self.patterns = self.read(config_path)

    @classmethod
    def read(cls, config_path: str) -> Tuple[Set[str], Tuple]:
        word, pattern = [], []
        if not os.path.exists(config_path):
            return set(), ()
        for line in Path(config_path).read_text(encoding="UTF-8").splitlines():
            if line.startswith("r"):
                pattern.append(re.compile(line.replace("r", "").strip()))
            else:
                word.append(line.strip())
        return set(word), tuple(pattern)

    def is_exclude(self, word: str) -> bool:
        return not (word in self.data or any(p.search(word) for p in self.patterns))
