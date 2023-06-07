import datetime
from typing import Sequence, Iterator

from pydub import AudioSegment
from tqdm import tqdm

from zunda_w.srt_ops import SpeakerCompose, merge


def millisecond(t: datetime.timedelta) -> float:
    return int(t.total_seconds() * 1000 + t.microseconds / 1000.0)


def concatenate(segment: Iterator[AudioSegment]) -> AudioSegment:
    empty = AudioSegment.empty()
    for audio in segment:
        empty += audio
    return empty


def concatenate_from_file(wav_files: Iterator[str]) -> AudioSegment:
    """
    音声ファイルを順番に結合
    """
    return concatenate(map(AudioSegment.from_file, wav_files))


def arrange(compose: SpeakerCompose) -> AudioSegment:
    """
    SpeakerComposeをAudioSegmentに再構成
    :param compose:
    :return:
    """
    ms = millisecond(compose.audio_duration)
    empty = AudioSegment.silent(ms, 44100)
    next_sum = 0
    start_point = []
    zunda_duration = []
    for unit in compose.unit:  # tqdm(compose.unit, desc='Audio composing', unit='wav'):
        seg = unit.audio
        srt = unit.subtitle
        srt_duration = millisecond((srt.end - srt.start))
        duration = len(seg)  # millsecond(float)
        scale = duration / float(srt_duration)
        diff = duration - srt_duration
        start_ms = next_sum
        start_point.append(start_ms)
        zunda_duration.append(duration)
        next_sum += duration
        empty = empty.overlay(seg, position=start_ms)
    return empty
