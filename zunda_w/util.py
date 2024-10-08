import hashlib
import json
import os
from pathlib import Path
from typing import Sequence, Union, Optional

import srt
import yaml
from loguru import logger


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


def search(srts: Sequence[srt.Subtitle], index: Optional[int]=None, proprietary: Optional[str] = None) -> Optional[
    srt.Subtitle]:
    """
    srtの中からindexかproprietaryで検索する
    検索の順番はindex > proprietaryで行う.

    :param srts:
    :param index:
    :param proprietary:
    :return:
    """
    tmp = None
    if index:
        tmp = filter(lambda x: x.index == index, srts)
    if proprietary:
        tmp = filter(lambda x: x.proprietary == proprietary, tmp)
    if tmp:
        return next(tmp, None)

def search_index(srts: Sequence[srt.Subtitle], index: Optional[int]=None, proprietary: Optional[str] = None)-> Optional[int]:
    item = search(srts, index, proprietary)
    if item:
        return srts.index(item)

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


def read_preset(preset_name: str, preset_dir: str):
    publish_conf_path = os.path.join(preset_dir, f"{preset_name}.yml")
    if not os.path.exists(publish_conf_path):
        logger.warning(f"Not Found Publish Preset: {publish_conf_path}")
        return None

    return yaml.load(open(publish_conf_path), Loader=yaml.SafeLoader)
