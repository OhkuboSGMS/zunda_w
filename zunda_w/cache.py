import os
from pathlib import Path
from typing import Callable, Tuple


def user_cache_dir(name: str) -> str:
    """
    hugging_face,whisper,firebaseなどと同様のパスのキャッシュフォルダを作成
    :param name:
    :return:
    """
    cache_dir = os.path.join(os.path.expanduser('~'), '.cache', name)
    if not os.path.exists(cache_dir):
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
    return cache_dir


def cached_file(output_file: str, func: Callable[[], str]) -> Tuple[bool, str]:
    """
    output_fileがあればそのファイルパスを返す.
    無ければfuncを実行してその結果を返す．
    funcのreturnはstr指定.

    :param output_file:
    :param func:
    :return:
    """
    if os.path.exists(output_file):
        return True, output_file
    return False, func()
