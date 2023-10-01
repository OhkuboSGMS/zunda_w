from typing import List

from loguru import logger

from zunda_w.llm.convert_word_to_kana import word_to_kana

_cmd_dict = {"word2kana": word_to_kana}


def post_process(srt_file: str, cmd_list: List[str]) -> str:
    if len(cmd_list) == 0:
        logger.debug("No Command.Skip srt post process.")
        return srt_file
    for cmd in cmd_list:
        if cmd not in _cmd_dict:
            logger.warning(f"{cmd} not found in Command List!. Check command name.")
            continue
        srt_file = _cmd_dict[cmd](srt_file)
    return srt_file
