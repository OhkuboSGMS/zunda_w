import hashlib
from pathlib import Path
from typing import Union, Tuple, Optional
from urllib import request
from urllib.error import HTTPError
from urllib.parse import urlparse

from loguru import logger
from tqdm import tqdm

from zunda_w import util
from zunda_w.voicevox_download_link import _hash_func


class _DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_url(url: str, output_path: str):
    with _DownloadProgressBar(unit='B', unit_scale=True,
                              miniters=1, desc=url.split('/')[-1]) as t:
        request.urlretrieve(url, filename=output_path, reporthook=t.update_to)


# https://github.com/OhkuboSGMS/NullA/blob/develop/nulla/download.py
def cache_download_from_github(url: str, hash_name: str, save_dir: Union[str, Path], force_download: bool = False) -> \
        Tuple[
            bool, Optional[Path]]:
    """
    キャッシュがあるかチェックしてからダウンロードする.
    現在ダウンロードされているファイルとhash_nameが一致しなければ
    何らかの問題でダウンロードされたに欠陥があるため，再度ダウンロードする.

    :param url:
    :param hash_name:ダウンロードしたファイルのハッシュ値.正常なダウンロードかチェックする
    :param save_dir:
    :param force_download: キャッシュに問わず強制的にダウンロードする
    :return:
    """
    file_name = Path(urlparse(url).path).name
    save_path = Path(save_dir).joinpath(file_name)
    if save_path.exists():
        hash_func = getattr(hashlib, _hash_func)
        if force_download:
            return download_from_github(url, save_dir)
        if util.file_hash(str(save_path), hash_func) != str.lower(hash_name):
            logger.warning(f'exists file not valid. re-download from url:{save_path}')
            return download_from_github(url, save_dir)

        return True, save_path
    else:
        return download_from_github(url, save_dir)


def download_from_github(url: str, save_dir: Union[str, Path]) -> Tuple[bool, Optional[Path]]:
    """
    githubからファイルをダウンロード. rawファイルのURLを使用する必要がある.
    :param url: ダウンロードURL.末端パスをファイル名に使用
    :param save_dir: ファイルを保存するディレクトリ
    :return: ダウンロード結果,ファイルパス
    """
    save_dir = Path(save_dir)
    file_name = Path(urlparse(url).path).name
    if not save_dir.exists():
        save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir.joinpath(file_name)
    try:
        download_url(url, save_path)
        return True, save_path
    except HTTPError as http:
        print(http)
        return False, None

    return False, None
