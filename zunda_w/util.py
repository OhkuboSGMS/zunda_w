import hashlib
import json
from pathlib import Path
from typing import Union


def file_hash(path: Union[str, Path], hash_fun=hashlib.md5) -> str:
    with open(path, 'rb') as fp:
        return hash_fun(fp.read()).hexdigest()


def try_json_parse(json_path: str) -> bool:
    try:
        json.loads(Path(json_path).read_text(encoding='UTF-8'))
        return True
    except  json.JSONDecodeError:
        return False
