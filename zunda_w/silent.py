import os.path
from pathlib import Path
from typing import Tuple, List
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from loguru import logger
from pydub import AudioSegment, silence
from pydub import effects


@dataclass_json
@dataclass
class Segment:
    start: int
    end: int


def _divide_by_silence(segment: AudioSegment, min_silence_len=4000, seek_step=10, silence_thresh_down=-20,
                       min_length=500) -> List[Tuple[int, AudioSegment, Segment]]:
    dbFS = segment.dBFS
    result = silence.detect_nonsilent(segment,
                                      min_silence_len=min_silence_len,
                                      seek_step=seek_step,
                                      silence_thresh=dbFS + silence_thresh_down
                                      )

    segments = []
    idx = 0
    for i, (s, e) in enumerate(result):
        duration = (e - s)
        # print(f'duration: {duration / 1000}s')
        # 検出した音声が最小音声長(millisecond)より短いものは採用しない
        if duration < min_length:
            # print(f'skip audio :{i}')
            continue
        logger.debug(
            f'[{idx:04d}] {int(s / 1000 / 60):02d}:{int(s / 1000 % 60):02d}:{int(s % 1000):03d} -> '
            f'{int(e / 1000 / 60):02d}:{int(e / 1000 % 60):02d}:{int(e % 1000):03d}')
        slice = segment[s:e]
        seg = Segment(s, e)
        idx += 1
        segments.append((idx, slice, seg))
    return segments


def divide_by_silence(wave_file: str, min_silence_len=4000, seek_step=10, silence_thresh_down=-20,
                      min_length=500,
                      root_dir: str = os.curdir, output_dir: str = '.silence') -> Tuple[Tuple[str], Tuple[str]]:
    logger.debug(f'divide by silence:{wave_file}')
    segment = AudioSegment.from_file(wave_file)
    logger.debug('Effect : Normalize')
    segment = effects.normalize(segment)
    output_dir = Path(root_dir).joinpath(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.debug(f'dBFS:{segment.dBFS}')
    dbFS = segment.dBFS
    result = silence.detect_nonsilent(segment,
                                      min_silence_len=min_silence_len,
                                      seek_step=seek_step,
                                      silence_thresh=dbFS + silence_thresh_down
                                      )

    segments = []
    audios = []
    idx = 0
    for i, (s, e) in enumerate(result):
        duration = (e - s)
        # print(f'duration: {duration / 1000}s')
        # 検出した音声が最小音声長(millisecond)より短いものは採用しない
        if duration < min_length:
            # print(f'skip audio :{i}')
            continue
        logger.debug(
            f'[{idx:04d}] {int(s / 1000 / 60):02d}:{int(s / 1000 % 60):02d} -> {int(e / 1000 / 60):02d}:{int(e / 1000 % 60):02d}')
        slice = segment[s:e]
        output_path = os.path.join(output_dir, f'{idx:04d}.wav')
        seg = Segment(s, e)
        segment_path = Path(output_path).with_suffix('.meta')
        segment_path.write_text(Segment.to_json(seg, indent=2), encoding='UTF-8')

        slice.export(output_path)
        segments.append(str(segment_path))
        audios.append(output_path)
        idx += 1

    return tuple(segments), tuple(audios)
