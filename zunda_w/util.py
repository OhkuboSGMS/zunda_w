import hashlib
import json
from pathlib import Path
from typing import Sequence, Union

import srt


def file_hash(path: Union[str, Path], hash_fun=hashlib.md5) -> str:
    with open(path, "rb") as fp:
        return hash_fun(fp.read()).hexdigest()


def text_hash(content: Union[bytes, str], hash_fun=hashlib.md5) -> str:
    if type(content) == str:
        content = content.encode()
    return hash_fun(content).hexdigest()


def try_json_parse(json_path: str) -> bool:
    try:
        json.loads(Path(json_path).read_text(encoding="UTF-8"))
        return True
    except json.JSONDecodeError:
        return False


def write_json(data: dict, json_path: Union[str, Path]):
    with open(json_path, "w") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=False)
    return json_path

def write_srt(
        path: Union[str, Path],
        data: Sequence[srt.Subtitle],
        encoding: str = "UTF-8",
        reindex=False,
):
    Path(path).write_text(srt.compose(data, reindex=reindex), encoding=encoding)


def read_srt(path: Union[str, Path], encoding: str = "UTF-8") -> Sequence[srt.Subtitle]:
    return list(srt.parse(Path(path).read_text(encoding=encoding)))


def display_file_uri(path: str, print_func=print):
    """
    ターミナルでクリックすると表示できる方式で画面出力する
    :param path:
    :param print_func:
    :return:
    """
    print_func(Path(path).absolute().as_uri())


def file_uri(path: str) -> str:
    return Path(path).absolute().as_uri()


def read_json(json_file: Union[str, Path]) -> dict:
    return json.loads(Path(json_file).read_text())
