from __future__ import annotations

import json
import os
import platform
import subprocess
import time
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from typing import Sequence, Generator, List, Union, Optional, TypedDict, Dict, Iterator, Tuple

import py7zr
import requests
import srt
from dataclasses_json import dataclass_json
from loguru import logger
from pydub import AudioSegment

from zunda_w.download import cache_download_from_github
from zunda_w.voicevox_download_link import _engines, _engines_sha256

# TODO ポート番号の仕様チェック
ROOT_URL = 'http://localhost:50021'


class VoiceVoxProfile(TypedDict, total=False):
    speedScale: float
    pitchScale: float
    intonationScale: float
    volumeScale: float
    prePhonemeLength: float
    postPhonemeLength: float
    outputSamplingRate: float
    outputStereo: float


VoiceVoxProfiles = List[VoiceVoxProfile]


def replace_query(src_query: Dict, trt_query: Dict) -> Dict:
    ret_query = src_query.copy()
    for k, v in trt_query.items():
        ret_query[k] = v

    return ret_query


def _download_engine(urls: List[str], file_hash: List[str], cache_dir: str):
    """
    voicevox-engineをダウンロード.
    ダウンロード後解凍
    .engine/windows/ .7zip ,exe folder
    """
    assert len(urls) == len(file_hash)
    for url, h in zip(urls, file_hash):
        logger.debug(f'Download: {url}')
        success, save_path = cache_download_from_github(url, h, cache_dir, force_download=False)
        if not success:
            raise IOError(f'URL:{url} can\'t download')
        yield save_path


def _extract_multipart(archives: List[Union[str, Path]], directory: str):
    concat_file = 'concat.7z'
    Path(directory).mkdir(exist_ok=True, parents=True)
    logger.debug('Concat multipart files')
    with open(concat_file, 'wb') as outfile:
        for f in archives:
            with open(f, 'rb') as infile:
                outfile.write(infile.read())

    logger.debug(f'Extract: {concat_file}')
    with py7zr.SevenZipFile(concat_file, mode='r') as z:
        z.extractall(directory)
    os.unlink(concat_file)
    return directory


def extract_engine(root_dir: str = '.engine', directory: str = 'voicevox', dry_run: bool = False) -> Optional[str]:
    """
    voicevox-engineをダウンロード.ファイルに展開
    :param root_dir:
    :param directory:
    :param dry_run:実際にダウンロード等は行わず，実行可能かのみチェックする
    :return:
    """
    system = platform.system()
    if system not in _engines.keys():
        raise NotImplementedError(system)
    root_dir = Path(root_dir).joinpath(system)
    root_dir.mkdir(exist_ok=True, parents=True)
    exe_dir = root_dir.joinpath(directory)
    # check already extracted
    exe_path = list(exe_dir.glob('**/run.exe'))
    if exe_dir and len(exe_path) == 1:
        return str(exe_path[0])
    # download and extract exe
    else:
        if dry_run:
            return None
        logger.debug(f'Download voicevox-engine from github　-> {root_dir}')
        archives = list(_download_engine(_engines[system], _engines_sha256[system], str(root_dir)))
        exe_dir = _extract_multipart(archives, exe_dir)
        exe_path = list(Path(exe_dir).glob('**/run.exe'))
        return str(exe_path[0])


def launch_voicevox_engine(exe_path: str) -> subprocess.Popen:
    return subprocess.Popen([exe_path, '--use_gpu'], stdout=subprocess.DEVNULL)


def synthesis(text: str, filename: str, speaker=1, max_retry=20, query: VoiceVoxProfile = None):
    # audio_query
    query_payload = {"text": text, "speaker": speaker}
    for query_i in range(max_retry):
        r = requests.post(f"{ROOT_URL}/audio_query",
                          params=query_payload, timeout=(10.0, 300.0))
        if r.status_code == 200:
            query_data = r.json()
            break
        time.sleep(1)
    else:
        raise ConnectionError("リトライ回数が上限に到達しました。 audio_query : ", filename, "/", text[:30], r.text)

    # synthesis
    synth_payload = {"speaker": speaker}
    query_data = replace_query(query_data, query)
    for synth_i in range(max_retry):
        r = requests.post(f"{ROOT_URL}/synthesis", params=synth_payload,
                          data=json.dumps(query_data), timeout=(10.0, 300.0))
        if r.status_code == 200:
            with open(filename, "wb") as fp:
                fp.write(r.content)
            return f'{text} -> {filename} '
    else:
        raise ConnectionError("リトライ回数が上限に到達しました。 synthesis : ", filename, "/", text[:30], r, text)


def output_path(idx: int, root: str) -> str:
    return os.path.join(root, f"audio_{idx :05d}.wav")


def read_output_waves(wave_dir: str) -> Generator[AudioSegment, None, None]:
    # os.listdirに順序性は保証されていないのでソート
    for src in sorted(os.listdir(wave_dir)):
        yield AudioSegment.from_file(os.path.join(wave_dir, src))


def text_to_speech(contents: Sequence[str], speaker: int, output_dir: str, query: VoiceVoxProfile):
    with ThreadPoolExecutor() as executor:
        futures = []
        for i, line in enumerate(contents):
            futures.append(executor.submit(synthesis, line, output_path(i, output_dir), speaker=speaker, query=query))
        for result in as_completed(futures):
            logger.debug(result.result())
    return output_dir


def run(srt_file: str, root_dir: str, speaker: int = 1, query: VoiceVoxProfile = None,
        output_dir: str = '.tts'):
    output_dir = Path(root_dir).joinpath(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if query is None:
        query = VoiceVoxProfile()

    subtitles = srt.parse(Path(srt_file).read_text(encoding='utf-8'))
    subtitles = list(map(lambda x: x.content, subtitles))
    return text_to_speech(subtitles, speaker, str(output_dir), query)


def get_speakers(write_path: Optional[str] = None) -> Optional[str]:
    r = requests.get(f"{ROOT_URL}/speakers", )
    if r.status_code == 200:
        query_data = r.json()
        data = json.dumps(query_data, indent=2, ensure_ascii=False)
        if write_path:
            Path(write_path).write_text(data, encoding='UTF-8')
        return data
    return None


def get_speaker_info(speaker_id: int, data: List) -> str:
    _id_dict = {int(kv[0]): kv[1] for kv in
                chain.from_iterable(
                    map(lambda d: map(lambda x: (x['id'], d['name'] + '_' + x['name'],), d['styles']), data))}
    if speaker_id not in _id_dict:
        return str(speaker_id)
    else:
        return _id_dict[speaker_id]


def add_word(word: str, pronunce: str, accent_type: int = 1):
    query_payload = {"surface": word, "pronunciation": pronunce, "accent_type": accent_type}

    r = requests.get(f"{ROOT_URL}/user_dict_word",
                     params=query_payload, timeout=(10.0, 300.0))
    if r.status_code == 200:
        query_data = r.json()


if __name__ == '__main__':
    voicevox_process = None
    try:
        exe_path = extract_engine(root_dir='.test')
        voicevox_process = launch_voicevox_engine(exe_path)

    except KeyboardInterrupt:
        if voicevox_process:
            voicevox_process.terminate()
            voicevox_process.poll()
