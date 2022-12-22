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
from typing import Sequence, Generator, List, Optional, TypedDict, Dict, Iterator, Tuple

import requests
import srt
from dataclasses_json import dataclass_json
from loguru import logger
from pydub import AudioSegment

from zunda_w.cache import cached_file
from zunda_w.download_voicevox import extract_engine

# TODO ポート番号の仕様チェック
from zunda_w.hash import concat_hash, dict_hash

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


@dataclass_json
@dataclass
class Style:
    id: int
    name: str


@dataclass_json
@dataclass
class Speaker:
    name: str
    speaker_uuid: str
    styles: List[Style]
    version: str

    def as_style_names(self) -> List[str]:
        return list(map(lambda s: f'{self.name}({s.name})', self.styles))

    def as_style_ids(self) -> List[int]:
        return list(map(lambda s: s.id, self.styles))


@dataclass
class Speakers:
    data: List[Speaker]

    @classmethod
    def read(cls, path) -> Speakers:
        with open(path, encoding='UTF-8') as fp:
            return Speakers(data=Speaker.schema().load(json.load(fp), many=True))

    def as_view(self) -> Dict[int, str]:
        """
        selectbox用に変換
        :return:Dict[style_id,style_name(speaker_name(style_name))]
        """
        _data: Iterator[Tuple[int, str]] = chain.from_iterable(
            map(lambda speaker: zip(speaker.as_style_ids(), speaker.as_style_names()), self.data))
        return {style_id: style_name for style_id, style_name in _data}


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
