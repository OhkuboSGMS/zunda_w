from typing import List, Dict, Callable

from loguru import logger

from zunda_w.llm.convert_word_to_kana import word_to_kana
from zunda_w.postprocess.dummy import dummy
from zunda_w.sentence.sentiment import add_emotion_tag

_cmd_dict: Dict[str, Callable[[str], str]] = {
    "word2kana": word_to_kana,
    "dummy": dummy,
    "emotion_analysis": add_emotion_tag,
    # sentiment_analysis
}


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
