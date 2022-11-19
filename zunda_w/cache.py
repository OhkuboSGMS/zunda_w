import os
from pathlib import Path


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
