import hashlib
import json
from pathlib import Path
from typing import Union, Sequence

import srt


def file_hash(path: Union[str, Path], hash_fun=hashlib.md5) -> str:
    with open(path, 'rb') as fp:
        return hash_fun(fp.read()).hexdigest()


def text_hash(content: Union[bytes, str], hash_fun=hashlib.md5) -> str:
    if type(content) == str:
        content = content.encode()
    return hash_fun(content).hexdigest()


def try_json_parse(json_path: str) -> bool:
    try:
        json.loads(Path(json_path).read_text(encoding='UTF-8'))
        return True
    except json.JSONDecodeError:
        return False


def write_srt(path: Path, data: Sequence[srt.Subtitle], encoding: str = 'UTF-8', reindex=False):
    path.write_text(srt.compose(data, reindex=reindex), encoding=encoding)


def read_srt(path: Path, encoding: str = 'UTF-8') -> Sequence[srt.Subtitle]:
    return list(srt.parse(path.read_text(encoding=encoding)))
