from __future__ import annotations

import json
import os
import subprocess
import time
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from functools import partial
from itertools import chain, repeat
from pathlib import Path
from typing import (
    Dict,
    Generator,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
)

import requests
import srt
from dataclasses_json import dataclass_json
from loguru import logger
from pydub import AudioSegment

from zunda_w.cache import cached_file
from zunda_w.hash import concat_hash, dict_hash
from zunda_w.voicevox.voicevox_user_dict import parse_user_dict_from_csv
from zunda_w.postprocess.srt import tag

# TODO ポート番号の仕様チェック
ROOT_URL = "http://localhost:50021"


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
    logger.debug(f"[VOICEVOX] Launch {exe_path} as subprocess")
    return subprocess.Popen([exe_path, "--use_gpu"], stdout=subprocess.DEVNULL)


@contextmanager
def voicevox_engine(exe_path: str):
    voicevox_process = None
    try:
        voicevox_process = launch_voicevox_engine(exe_path)
        logger.debug("wait voicevox")
        wait_until_voicevox_ready()
        yield voicevox_process
    except Exception as e:
        logger.exception(e)
    finally:
        if voicevox_process:
            voicevox_process.terminate()
            voicevox_process.poll()


def _request_and_write(filename: str, synth_payload, query_data) -> Optional[str]:
    r = requests.post(
        f"{ROOT_URL}/synthesis",
        params=synth_payload,
        data=json.dumps(query_data),
        timeout=(10.0, 300.0),
    )
    if r.status_code == 200:
        # 別スレッドで既に保存されている可能性も考慮.
        if os.path.exists(filename):
            return filename

        with open(filename, "wb") as fp:
            fp.write(r.content)
            fp.flush()
            os.fsync(fp.fileno())
        return filename
    return None


def synthesis(
        text: str,
        speaker: int,
        output_name: Optional[str],
        output_dir: str,
        max_retry=20,
        query: VoiceVoxProfile = None,
        use_cache=True,
):
    """
    voicevoxにて合成音声を出力
    :param text:
    :param output_dir:
    :param output_name: 出力ファイル名.Noneの場合queryから計算
    :param speaker:
    :param max_retry:
    :param query:
    :param use_cache: False,強制的に上書きする
    :return:
    """
    # check text is tag
    if tag.contain_tag(text, '[next]'):
        empty_audio_file = 'empty'
        return empty_audio_file
    # audio_query
    query_payload = {"text": text, "speaker": speaker}
    for query_i in range(max_retry):
        r = requests.post(
            f"{ROOT_URL}/audio_query", params=query_payload, timeout=(10.0, 300.0)
        )
        if r.status_code == 200:
            query_data = r.json()
            break
        time.sleep(1)
    else:
        raise ConnectionError(
            "リトライ回数が上限に到達しました。 audio_query : ", output_dir, "/", text[:30], r.text
        )

    # synthesis
    synth_payload = {"speaker": speaker}
    query_data = replace_query(query_data, query)
    # リクエストパラメータからキャッシュ値を計算
    cache_hash: str = str(concat_hash([dict_hash(query_data)]))
    if output_name:
        output_file = os.path.join(output_dir, f"{output_name}.wav")
    else:
        output_file = os.path.join(output_dir, f"{cache_hash}.wav")
    if not use_cache and os.path.exists(output_file):
        os.unlink(output_file)
    for synth_i in range(max_retry):
        if use_cache:
            cached, output_file_name = cached_file(
                output_file,
                lambda: _request_and_write(output_file, synth_payload, query_data),
            )
        else:
            cached, output_file_name = False, _request_and_write(
                output_file, synth_payload, query_data
            )
        if output_file_name is not None:
            logger.debug(
                f'{text[:15].ljust(15)} ->{"[cache] " if cached else ""} {output_file_name} '
            )
            return output_file_name
    else:
        raise ConnectionError(
            "リトライ回数が上限に到達しました。 synthesis : ", output_dir, "/", text[:30], r, text
        )


def synthesis_map(data: Tuple[str, int, Optional[str]], output_dir: str, query: VoiceVoxProfile, use_cache: bool):
    return synthesis(
        data[0],
        data[1],
        data[2],
        output_dir=output_dir,
        query=query,
        use_cache=use_cache,
    )


def output_path(idx: int, root: str) -> str:
    return os.path.join(root, f"audio_{idx :05d}.wav")


def read_output_waves(wave_files: Sequence[str]) -> Generator[AudioSegment, None, None]:
    for src in wave_files:
        yield AudioSegment.from_file(src)


def read_output_waves_from_dir(wave_dir: str) -> Generator[AudioSegment, None, None]:
    """
    wave_dirから名前順でファイルを取得

    :param wave_dir:
    :return: Generator[AudioSegment]
    """
    # os.listdirに順序性は保証されていないのでソート
    # return read_output_waves(map(lambda src: os.path.join(wave_dir, src), sorted(os.listdir(wave_dir))))
    for src in sorted(os.listdir(wave_dir)):
        yield AudioSegment.from_file(os.path.join(wave_dir, src))


def text_to_speech_order(
        contents: Sequence[str],
        speaker: Sequence[int],
        output_dir: str,
        query: VoiceVoxProfile,
        output_names: Optional[Sequence[str]] = None,
        use_cache: bool = False,
) -> Sequence[str]:
    if output_names is None:
        output_names = [None for _ in range(len(contents))]
    elif len(contents) != len(output_names):
        raise ValueError("output_names length not equal contents")
    with ThreadPoolExecutor() as executor:
        results = []
        for result in executor.map(
                partial(
                    synthesis_map, output_dir=output_dir, query=query, use_cache=use_cache
                ),
                zip(contents, speaker, output_names),
        ):
            logger.debug(result)
            results.append(result)
    return results


def text_to_speech(
        contents: Sequence[str], speaker: int, output_dir: str, query: VoiceVoxProfile
) -> str:
    """
    VoiceVoxローカルサーバに対してリクエストを投げてttsを実行.

    :param contents:
    :param speaker:
    :param output_dir:
    :param query:
    :return: 出力したフォルダ
    """
    with ThreadPoolExecutor() as executor:
        futures = []
        for i, line in enumerate(contents):
            futures.append(
                executor.submit(
                    synthesis, line, output_dir, speaker=speaker, query=query
                )
            )
        for result in as_completed(futures):
            logger.debug(result.result())
    return output_dir


def run(
        srt_file: Union[str, Sequence[srt.Subtitle]],
        root_dir: str,
        speaker: Union[None, int, Sequence[int]] = None,
        query: VoiceVoxProfile = None,
        output_dir: str = ".tts",
        output_names: Optional[Sequence[str]] = None,
        use_cache: bool = True,
):
    """
    srt(text) to speech を実行.
    出力した音声ファイルはsrtファイルの順番と一致する
    :param srt_file:
    :param root_dir: 音声合成出力フォルダ
    :param speaker: Noneではsrt_fileのメタデータを参照
    :param query:
    :param output_dir:
    :param use_cache: Falseの場合キャッシュをつかわない
    :return:
    """
    output_dir = Path(root_dir).joinpath(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if query is None:
        query = VoiceVoxProfile()

    if type(srt_file) == str:
        subtitles = list(srt.parse(Path(srt_file).read_text(encoding="utf-8")))
    else:
        subtitles = srt_file
    if speaker is None:
        logger.debug("Speaker ID from srt file")
        speaker = list(map(lambda s: s.proprietary, subtitles))
    elif isinstance(speaker, Sequence):
        assert len(speaker) == len(
            srt_file
        ), "speakersがリストの場合,srt_fileとspeakersの個数は一致しなければいけません"
    else:
        speaker = list(repeat(speaker, len(subtitles)))

    subtitles = list(map(lambda x: x.content, subtitles))

    # 読み上げように，無駄な空白をなくす
    def non_empty(x: str) -> str:
        return "".join(filter(lambda c: c != " ", x))

    subtitles = list(map(non_empty, subtitles))

    return text_to_speech_order(
        subtitles,
        speaker,
        str(output_dir),
        query,
        output_names=output_names,
        use_cache=use_cache,
    )


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
        return list(map(lambda s: f"{self.name}({s.name})", self.styles))

    def as_style_ids(self) -> List[int]:
        return list(map(lambda s: s.id, self.styles))


@dataclass
class Speakers:
    data: List[Speaker]

    @classmethod
    def read(cls, path) -> Speakers:
        with open(path, encoding="UTF-8") as fp:
            return Speakers(data=Speaker.schema().load(json.load(fp), many=True))

    def as_view(self) -> Dict[int, str]:
        """
        selectbox用に変換
        :return:Dict[style_id,style_name(speaker_name(style_name))]
        """
        _data: Iterator[Tuple[int, str]] = chain.from_iterable(
            map(
                lambda speaker: zip(speaker.as_style_ids(), speaker.as_style_names()),
                self.data,
            )
        )
        return {style_id: style_name for style_id, style_name in _data}


def get_speakers(write_path: Optional[str] = None) -> Optional[List[Dict]]:
    r = requests.get(
        f"{ROOT_URL}/speakers",
    )
    if r.status_code == 200:
        query_data = r.json()
        data = json.dumps(query_data, indent=2, ensure_ascii=False)
        if write_path:
            Path(write_path).write_text(data, encoding="UTF-8")
        return query_data
    return None


def format_speaker(data: dict) -> str:
    text = []
    for character in data:
        name = character["name"]
        for s in character["styles"]:
            text.append(f'{s["id"]:2d} {name}({s["name"]})')
    return "\n".join(text)


def get_speaker_info(speaker_id: int, data: List) -> str:
    _id_dict = {
        int(kv[0]): kv[1]
        for kv in chain.from_iterable(
            map(
                lambda d: map(
                    lambda x: (
                        x["id"],
                        d["name"] + "_" + x["name"],
                    ),
                    d["styles"],
                ),
                data,
            )
        )
    }
    if speaker_id not in _id_dict:
        return str(speaker_id)
    else:
        return _id_dict[speaker_id]


def get_version():
    return requests.get(f"{ROOT_URL}/version")


def is_voicevox_launch(n_try: int = 5) -> bool:
    """
    voicevoxが立ち上がっているか確認
    :param n_try:
    :return:
    """
    version = get_version()
    for i in range(n_try):
        if version.status_code == 200:
            return True
    return False


def wait_until_voicevox_ready(timeout: float = 30):
    """
    /version で導通確認を行う
    :param timeout:
    :return:
    """
    start = time.perf_counter()
    while (time.perf_counter() - start) < timeout:
        try:
            logger.debug("waiting...")
            version = get_version()
            if version.status_code == 200:
                # 接続確認できたので終了
                break
        except Exception as e:
            logger.debug(f"waiting voicevox start...:{str(e)}")
            time.sleep(0.1)


def add_word(word: str, pronunce: str, accent_type: int = 1):
    query_payload = {
        "surface": word,
        "pronunciation": pronunce,
        "accent_type": accent_type,
    }

    r = requests.get(
        f"{ROOT_URL}/user_dict_word", params=query_payload, timeout=(10.0, 300.0)
    )
    if r.status_code == 200:
        query_data = r.json()


def import_word_csv(csv_file: str, override: bool = True):
    logger.debug("Import User Dict to Voicevox")
    if not os.path.exists(csv_file):
        logger.warning(f"Not Found: user word dict : {csv_file}")
        return
    word_map = parse_user_dict_from_csv(csv_file)
    r = requests.post(
        f"{ROOT_URL}/import_user_dict", params={"override": override}, json=word_map
    )
    if r.status_code == 204:
        logger.success("Import Success")
    else:
        logger.warning(f"Something Wrong:{r.content}")
