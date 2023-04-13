import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Iterator, Dict, Sequence, Any

import torch
import whisper
from dataclasses_json import dataclass_json
from loguru import logger
from tqdm import tqdm
from whisper import Whisper

from zunda_w.whisers_util import write_srt
from zunda_w import srt_ops
from zunda_w.silent import Segment
from zunda_w.util import text_hash

_model_cache: Dict[str, str] = {}


@dataclass_json()
@dataclass(frozen=True)
class WhisperProfile:
    model: Literal['tiny', 'small', 'base', 'medium', 'large'] = 'small'
    language: str = 'ja'
    prompt: str = ''


def _transcribe(model: Whisper, profile: WhisperProfile, audio_file: str, ):
    # match parameters whisper CLI default(best_of,fp16,beam_size,suppress_tokens...)
    return model.transcribe(audio=audio_file,
                            verbose=True,
                            language=profile.language,
                            fp16=True,
                            best_of=5,
                            beam_size=5,
                            suppress_tokens="-1",
                            logprob_threshold=None,
                            initial_prompt=profile.prompt
                            )


def _align_segment(seg: Dict, meta: Segment, idx: int) -> Dict:
    seg['start'] += meta.start / 1000.0
    seg['end'] += meta.start / 1000.0
    seg['id'] += idx
    return seg


def transcribe_non_silence(wave_files: List[str], meta_files: List[str], profile: WhisperProfile,
                           close_model: bool = False) -> Iterator[Dict]:
    logger.debug('Whisper profile:')
    logger.debug(profile)

    model = whisper.load_model(profile.model) if profile.model not in _model_cache else _model_cache[profile.model]

    idx = 0
    for audio_file, meta_file in tqdm(zip(wave_files, meta_files), desc='Whisper Speech to Text'):
        logger.debug(f'{audio_file},{meta_file}')
        meta = Segment.from_json(Path(meta_file).read_text(encoding='UTF-8'))
        result = _transcribe(model, profile, audio_file)
        result = list(map(lambda seg: _align_segment(seg, meta, idx), result['segments']))
        idx += len(result)
        yield result
    if close_model:
        del model
        _model_cache.pop(profile.model)

    torch.cuda.empty_cache()


def transcribe_non_silence_srt(wave_files: Sequence[str], meta_files: Sequence[str], profile: WhisperProfile,
                               root_dir: str = os.curdir, output_dir: str = '.stt', meta_data: Any = '') -> str:
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
    encoding = 'UTF-8'
    file_name = text_hash(profile.to_json().encode(encoding=encoding))
    output_srt_path = output_dir.joinpath(file_name).with_suffix('.srt')
    logger.debug(f'srt path{output_srt_path} hash:{profile.__hash__()}')
    if output_srt_path.exists():
        logger.debug('Skip Whisper transcribe use cache.')
        return str(output_srt_path)
    srts = []
    for result in transcribe_non_silence(wave_files, meta_files, profile):
        srts.extend(result)

    with open(output_srt_path, "w", encoding=encoding) as srt_file:
        write_srt(srts, file=srt_file)
    if meta_data:
        srt_ops.write_srt_with_meta(output_srt_path, meta_data, encoding=encoding)
    return str(output_srt_path)


def transcribe_with_config(wave_files: List[str], profile: WhisperProfile, root_dir: str = os.curdir,
                           output_dir: str = '.stt', close_model: bool = False, meta_data: Any = '') -> List[str]:
    output_dir = Path(root_dir).joinpath(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    model = whisper.load_model(profile.model) if profile.model not in _model_cache else _model_cache[profile.model]
    encoding = 'UTF-8'
    for audio_file in tqdm(wave_files, desc='Whisper Speech to Text'):
        file_name = Path(audio_file).stem
        result = _transcribe(model, profile, audio_file)
        output_srt_path = output_dir.joinpath(file_name).with_suffix('.srt')
        with open(output_srt_path, "w", encoding=encoding) as srt_file:
            write_srt(result["segments"], file=srt_file)
        if meta_data:
            srt_ops.write_srt_with_meta(output_srt_path, meta_data, encoding=encoding)
        yield output_srt_path

    if close_model:
        del model
        _model_cache.pop(profile.model)
    torch.cuda.empty_cache()
