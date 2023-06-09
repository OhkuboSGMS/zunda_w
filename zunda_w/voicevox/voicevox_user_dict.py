import csv
import uuid
from pathlib import Path
from typing import Dict, Tuple, List

from voicevox_engine_user_dict.user_dict import create_word
from voicevox_engine_user_dict.model import WordTypes, UserDictWord


def enum_from_str(enum_cls, s: str):
    try:
        return enum_cls[s.upper()]
    except KeyError:
        raise ValueError(f"{s} is not a valid {str(enum_cls)}")


def parse_line(line: List[str]) -> Tuple[str, str, str, str]:
    if len(line) == 4:
        tmp = line
    elif len(line) == 3:
        tmp = [*line, 'PROPER_NOUN']
    elif len(line) == 2:
        tmp = [*line, '1', 'PROPER_NOUN']
    else:
        raise ValueError(f'Not Acceptable User Word : {line}')

    if not tmp[0] or not tmp[1]:
        raise ValueError(f'Not Set Word and Spoken')

    if not tmp[2]:
        tmp[2] = '1'
    if not tmp[3]:
        tmp[3] = 'PROPER_NOUN'
    return tuple(tmp)


def line_to_word(x: Tuple[str, str, str, str]):
    return create_word(x[0], x[1], int(x[2]), enum_from_str(WordTypes, x[3]))


# voicevoxのimport_user_dictに対応する形にcsvから変換する
def parse_user_dict_from_csv(file: str) -> Dict[str, Dict]:
    lines = list(csv.reader(Path(file).read_text(encoding='utf-8').splitlines()))
    words = list(map(line_to_word, map(parse_line, lines)))
    return {str(uuid.uuid4()): word.dict() for word in words}
