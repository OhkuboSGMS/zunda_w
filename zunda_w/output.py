import os.path
from datetime import datetime
from pathlib import Path
from typing import Final, Optional

DATE_FORMAT = "%Y%m%d_%H%M%S"


def directory_name() -> str:
    return datetime.now().strftime(DATE_FORMAT)


class OutputDir:
    def __init__(self, directory: Optional[str] = None, parent: str = os.getcwd()):
        _dir = Path(directory) if directory else Path(directory_name())
        self.directory: Final[Path] = Path(parent).joinpath(_dir)
        if not os.path.exists(self.directory):
            os.makedirs(self.directory, exist_ok=True)

    def __call__(self, file_name: str) -> Path:
        return self.directory.joinpath(file_name)
