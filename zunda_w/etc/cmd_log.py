# 実行時の引数をログに残す
from pathlib import Path
from typing import Sequence

from loguru import logger

# https://loguru.readthedocs.io/en/stable/api/logger.html
logger.add(".cmd.log", format="{time} | {message}", filter="zunda_w.etc.cmd_log")


def commit(argv: Sequence[str] = ("", "")):
    cmd, *args = argv
    cmd = Path(cmd).stem
    if type(args) == str:
        args = list(args)
    args = " ".join(args)
    logger.debug(f"{cmd} {args}")
