import contextlib
import copy
import hashlib
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Literal, Sequence

import whisper
from dataclasses_json import dataclass_json
from loguru import logger
from pydub import AudioSegment, effects
from tqdm import tqdm
from whisperx.types import AlignedTranscriptionResult, SingleAlignedSegment

from zunda_w import srt_ops
from zunda_w.model_cache import ModelCache
from zunda_w.silent import Segment
from zunda_w.util import text_hash
from zunda_w.whisper_util import write_srt

_in_memory_cache = ModelCache()


class ModelSize(Enum):
    tiny = "tiny"
    small = "small"
    base = "base"
    medium = "medium"
    large = "large"


@dataclass_json()
@dataclass(frozen=False)
class WhisperProfile:
    model: ModelSize = ModelSize.small
    language: str = "ja"
    prompt: str = ""

    def __hash__(self):
        data = f"{self.model}-{self.language}-{self.prompt}".encode("utf-8")
        return hashlib.md5(data).hexdigest()


def clean_model():
    logger.debug("Clean Text to Speech Models")
    _in_memory_cache.clear()


@contextlib.contextmanager
def whisper_context():
    yield
    clean_model()


def _transcribe_with_whisper_x(
    profile: WhisperProfile, audio_file: str
) -> AlignedTranscriptionResult:
    import whisperx

    logger.info("transcribe with whisper x")
    device = "cuda"
    batch_size = 1  # reduce if low on GPU mem
    compute_type = "float16"  # change to "int8" if low on GPU mem (may reduce accuracy)
    model_size = "large-v2"
    need_cache = False
    options = {
        "initial_prompt": profile.prompt,
        "no_speech_threshold": None,
    }
    if not _in_memory_cache.exist("whisper_x", model_size):
        # if model_name not in _model_cache_whisper_x:
        model = whisperx.load_model(
            "large-v2",
            device,
            compute_type=compute_type,
            language=profile.language,
            asr_options=options,
        )
        need_cache = True
    else:
        logger.debug("Use Model Cache")
        model = _in_memory_cache.get("whisper_x", model_size)[0]
    result = model.transcribe(
        audio_file,
        batch_size=batch_size,
        language=profile.language,
    )
    if not _in_memory_cache.exist("whisper_x", model_size):
        model_a, metadata = whisperx.load_align_model(
            language_code=result["language"], device=device
        )
    else:
        model_a, metadata = _in_memory_cache.get("whisper_x", model_size)[1]
    result_aligned = whisperx.align(
        result["segments"], model_a, metadata, audio_file, device
    )
    # whisper_xの出力するsegmentsにはidが無いので設定
    for i in range(len(result_aligned["segments"])):
        result_aligned["segments"][i]["id"] = i
    if need_cache:
        _in_memory_cache.add("whisper_x", model_size, (model, (model_a, metadata)))
    return result_aligned


def _transcribe_whisper(profile: WhisperProfile, audio_file: str):
    # match parameters whisper CLI default(best_of,fp16,beam_size,suppress_tokens...)
    logger.info("transcribe with whisper")
    if not _in_memory_cache.exist("whisper", profile.model):
        model = whisper.load_model(profile.model)
        _in_memory_cache.add("whisper", profile.model, model)
    else:
        model = _in_memory_cache.get("whisper", profile.model)

    return model.transcribe(
        audio=audio_file,
        verbose=True,
        language=profile.language,
        fp16=True,
        best_of=5,
        beam_size=5,
        suppress_tokens="-1",
        logprob_threshold=None,
        initial_prompt=profile.prompt,
        no_speech_threshold=None,
    )


def find_last_end(words: List[Dict]) -> float:
    for i in range(len(words) - 1, -1, -1):
        if "end" in words[i]:
            return words[i]["end"]


def _divide_segment(segment: SingleAlignedSegment, offset: int) -> List[Dict]:
    """
    whisperXの文字起こし後のポストプロセス．
    30秒以上の認識ができるため，絶え間なく話し続けている場合は，1行が
    長文で記述されるため，ちょうどいいサイズに区切れるよう調整．
    句読点が検出され，文章が20文字以上かつ，start,endの値が見つかった場合に文章を分割する
    :param segment:
    :param offset:
    :return:
    """
    # .。は即時分解
    #  '.'は日本語で出ないと仮定して外す
    punch = {",": 20, "、": 20, "。": 0}
    idx = offset
    sentence = []
    words = []
    start, end = segment["start"], segment["end"]
    for i in range(len(segment["words"])):
        chr = segment["words"][i]
        if "start" not in chr:
            chr["start"] = start
        words.append(chr)
        if (
            chr["word"] in punch
            and find_last_end(words) is not None
            and len(words) >= punch[chr["word"]]
        ):
            sentence.append(
                {
                    "id": idx,
                    "start": words[0]["start"] if "start" in words[0] else start,
                    "end": find_last_end(words),
                    "text": "".join(map(lambda x: x["word"], words)),
                }
            )
            start = find_last_end(words)  # chr['end']
            words = []
            idx += 1

    if len(words) > 0:
        sentence.append(
            {
                "id": idx,
                "start": words[0]["start"],
                "end": find_last_end(words) or end,
                "text": "".join(map(lambda x: x["word"], words)),
            }
        )
    return sentence


def _whisper_x_post_process(result: AlignedTranscriptionResult):
    """
    ルールに従って，word_segmentsからsegmentsを生成する
    :param result:
    :return:
    """
    id = 0
    original = copy.copy(result)
    segments = []
    for word in result["segments"]:
        sentence = _divide_segment(word, id)
        id += len(sentence)
        segments.extend(sentence)
    result["segments"] = segments
    return result


def _transcribe(model_name: str, profile: WhisperProfile, audio_file: str):
    if model_name == "whisper":
        return _transcribe_whisper(profile, audio_file)
    elif model_name == "whisper_x":
        _result = _transcribe_with_whisper_x(profile, audio_file)
        return _whisper_x_post_process(_result)


def _align_segment(seg: Dict, meta: Segment, idx: int) -> Dict:
    seg["start"] += meta.start / 1000.0
    seg["end"] += meta.start / 1000.0
    seg["id"] += idx
    return seg


def transcribe_non_silence(
    wave_files: List[str],
    meta_files: List[str],
    profile: WhisperProfile,
    close_model: bool = False,
) -> Iterator[Dict]:
    """
    無音区間をとりのぞいた分割音声で文字起しをす
    :param wave_files:
    :param meta_files:
    :param profile:
    :param close_model:
    :return:
    """
    logger.debug("Whisper profile:")
    logger.debug(profile)

    model = "whisper_x"
    idx = 0
    for audio_file, meta_file in tqdm(
        zip(wave_files, meta_files), desc="Whisper Speech to Text"
    ):
        logger.debug(f"{audio_file},{meta_file}")
        meta = Segment.from_json(Path(meta_file).read_text(encoding="UTF-8"))
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio = effects.normalize(AudioSegment.from_file(audio_file))
            tmp_file_path = Path(tmp_dir).joinpath(Path(audio_file).name)
            audio.export(tmp_file_path)

            result = _transcribe(model, profile, str(tmp_file_path))
        result = list(
            map(lambda seg: _align_segment(seg, meta, idx), result["segments"])
        )
        idx += len(result)
        yield result

    if close_model:
        clean_model()


def transcribe_non_silence_srt(
    wave_files: Sequence[str],
    meta_files: Sequence[str],
    profile: WhisperProfile,
    root_dir: str = os.curdir,
    output_dir: str = ".stt",
    meta_data: Any = "",
) -> str:
    """
    無音区間を切り抜いた音声ファイル列からsrtファイルを生成．

    :param wave_files:
    :param meta_files:
    :param profile:
    :param root_dir:
    :param output_dir:
    :param meta_data
    :return:
    """
    output_dir = Path(root_dir).joinpath(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    encoding = "UTF-8"
    file_name = text_hash(profile.to_json().encode(encoding=encoding))
    output_srt_path = output_dir.joinpath(file_name).with_suffix(".srt")
    logger.debug(f"srt path{output_srt_path} hash:{profile.__hash__()}")
    if output_srt_path.exists():
        logger.debug("Skip Whisper transcribe use cache.")
        return str(output_srt_path)
    srts = []
    i = 0
    for result in transcribe_non_silence(wave_files, meta_files, profile):
        logger.debug(f"{i} wav:{wave_files[i]},meta:{meta_files[i]}")
        srts.extend(result)
        i += 1

    with open(output_srt_path, "w", encoding=encoding) as srt_file:
        write_srt(srts, file=srt_file)
    if meta_data:
        srt_ops.write_srt_with_meta(output_srt_path, meta_data, encoding=encoding)
    return str(output_srt_path)


def transcribe_with_config(
    wave_files: List[str],
    profile: WhisperProfile,
    root_dir: str = os.curdir,
    output_dir: str = ".stt",
    close_model: bool = False,
    meta_data: Any = "",
) -> List[str]:
    """

    :param wave_files:
    :param profile:
    :param root_dir:
    :param output_dir:
    :param close_model:
    :param meta_data: 文字起こしした結果のsrtのproprietaryに設定するメタデータ
    :return:
    """
    output_dir = Path(root_dir).joinpath(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    model = "whisper_x"

    encoding = "UTF-8"
    for audio_file in tqdm(wave_files, desc="Whisper Speech to Text"):
        file_name = Path(audio_file).stem
        output_srt_path = output_dir.joinpath(file_name).with_suffix(".srt")
        # TODO 設定に基づくキャッシュを行う(現在はパラメータ関係なくキャッシュしている)b
        if output_srt_path.exists():
            logger.debug("Skip Whisper transcribe use cache.")
            yield str(output_srt_path)
            break
        with tempfile.TemporaryDirectory() as tmpdir:
            audio = effects.normalize(AudioSegment.from_file(audio_file))
            tmp_file_path = os.path.join(tmpdir, file_name)
            audio.export(tmp_file_path)
            result = _transcribe(model, profile, tmp_file_path)

        with open(output_srt_path, "w", encoding=encoding) as srt_file:
            write_srt(result["segments"], file=srt_file)
        if meta_data:
            srt_ops.write_srt_with_meta(output_srt_path, meta_data, encoding=encoding)
        yield str(output_srt_path)

    if close_model:
        clean_model()
