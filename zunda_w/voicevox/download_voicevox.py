from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import List, Optional, Union

import py7zr
from loguru import logger
from zipfile import ZipFile
from zunda_w.download import cache_download_from_github
from zunda_w.voicevox.voicevox_download_link import _engines, _engines_sha256


def _download_engine(urls: List[str], file_hash: List[str], cache_dir: str):
    """
    voicevox-engineをダウンロード.
    ダウンロード後解凍
    .engine/windows/ .7zip ,exe folder
    """
    assert len(urls) == len(file_hash)
    for url, h in zip(urls, file_hash):
        logger.debug(f"Download: {url}")
        success, save_path = cache_download_from_github(
            url, h, cache_dir, force_download=False
        )
        if not success:
            raise IOError(f"URL:{url} can't download")
        yield save_path


def _extract_multipart(archives: List[Union[str, Path]], directory: str):
    concat_file = "concat.7z"
    Path(directory).mkdir(exist_ok=True, parents=True)
    logger.debug("Concat multipart files")
    with open(concat_file, "wb") as outfile:
        for f in archives:
            with open(f, "rb") as infile:
                outfile.write(infile.read())

    logger.debug(f"Extract: {concat_file}")
    with py7zr.SevenZipFile(concat_file, mode="r") as z:
        z.extractall(directory)
    os.unlink(concat_file)
    return directory


def extract_engine(
        root_dir: str = ".engine",
        directory: str = "voicevox",
        dry_run: bool = False,
        update: bool = False,
) -> Optional[str]:
    """
    voicevox-engineをダウンロード.ファイルに展開
    :param root_dir:
    :param directory:
    :param dry_run:実際にダウンロード等は行わず，実行可能かのみチェックする
    :param update: ダウンロードの有無に関わらず，URLからダウンロードして展開する
    :return:
    """
    system = platform.system()
    if system not in _engines.keys():
        raise NotImplementedError(system)
    root_dir = Path(root_dir).joinpath(system)
    root_dir.mkdir(exist_ok=True, parents=True)
    exe_dir = root_dir.joinpath(directory)
    # check already extracted
    exe_path = list(exe_dir.glob("**/run.exe"))
    if not update and exe_dir and len(exe_path) == 1:
        return str(exe_path[0])
    # download and extract exe
    else:
        if dry_run:
            return None
        # 以前のダウンロードしたフォルダがある場合は削除
        if exe_dir.exists():
            shutil.rmtree(exe_dir)
        logger.debug(f"Download voicevox-engine from github　-> {root_dir}")
        archives = list(
            _download_engine(_engines[system], _engines_sha256[system], str(root_dir))
        )
        # archives extentions is 7z.001, 7z.002
        if len(archives) > 1 and str(archives[0]).endswith(".001"):
            exe_dir = _extract_multipart(archives, exe_dir)
            exe_path = list(Path(exe_dir).glob("**/run.exe"))
            return str(exe_path[0])
        elif len(archives) == 1 and archives[0].suffix == ".zip":
            # extract zip with zipfile
            shutil.unpack_archive(archives[0], exe_dir)
            return str(list(Path(exe_dir).glob("**/run.exe"))[0])
        else:
            raise NotImplementedError(f"Can't extract {archives}")
