import datetime
import os
from dataclasses import dataclass, field
from functools import cached_property
from itertools import chain
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple

import srt
from pydub import AudioSegment
from pydub.playback import play
from srt import Subtitle

from zunda_w.voicevox.voice_vox import read_output_waves
from zunda_w.words import WordFilter


@dataclass
class SpeakerUnit:
    subtitle: Subtitle
    audio_file_path: str
    audio: AudioSegment = field(init=False)

    def __post_init__(self):
        self.audio = AudioSegment.from_file(self.audio_file_path)

    def to_dict(self) -> dict:
        srt_dict = vars(self.subtitle)
        srt_dict["start"] = str(srt_dict["start"])
        srt_dict["end"] = str(srt_dict["end"])
        return {
            "subtitle": srt_dict,
            "audio_file": os.path.abspath(self.audio_file_path),
        }


@dataclass
class SpeakerCompose:
    unit: Tuple[SpeakerUnit]
    # whisper計測の会話総時間
    n_length: datetime.timedelta

    @staticmethod
    def from_srt(subtitles: Sequence[srt.Subtitle], tts_files: Sequence[str]):
        """
        srtファイルから合成音声を作成し，結合する場合にこのメソッドを使用する
        :param subtitles:
        :param tts_files:
        :return:
        """
        assert len(subtitles) == len(tts_files)
        compose = list(
            map(
                lambda x: SpeakerUnit(
                    x[0], AudioSegment.from_file(x[1]), audio_file_path=x[1]
                ),
                zip(subtitles, tts_files),
            )
        )
        last_end = subtitles[-1].end
        return SpeakerCompose(tuple(compose), last_end)

    def to_json(self) -> dict:
        return {
            "unit": [u.to_dict() for u in self.unit],
            "n_length": str(self.n_length),
        }

    @cached_property
    def audio_duration(self) -> datetime.timedelta:
        """
        unit.audioの総時間
        :return:
        """
        return datetime.timedelta(
            milliseconds=sum(map(lambda x: len(x.audio), self.unit))
        )

    @cached_property
    def srt(self) -> Sequence[srt.Subtitle]:
        return list(map(lambda u: u.subtitle, self.unit))

    def __str__(self) -> str:
        return "\n".join(map(str, self.unit))

    def playback(self):
        for unit in self.unit:
            play(unit.audio)


def _parse_with_id(
    srt_file_path: str, id: int, encoding: str, wave_paths: Sequence[str]
) -> List[SpeakerUnit]:
    subtitles = list(srt.parse(Path(srt_file_path).read_text(encoding=encoding)))
    for s in subtitles:
        s.speaker = id

    # audio = list(read_output_waves(wave_paths))
    return [SpeakerUnit(s, a) for s, a in zip(subtitles, wave_paths)]


def merge(
    srt_files: Sequence[str],
    tts_files: List[Sequence[str]],
    encoding="UTF-8",
    word_filter: WordFilter = None,
) -> SpeakerCompose:
    """
    SubtitleとAudiosを読み込み，時間順にソートする

    :return 合成結果のインスタンス
    """
    units: List[SpeakerUnit] = list(
        chain.from_iterable(
            map(
                lambda x: _parse_with_id(x[1][0], x[0], encoding, x[1][1]),
                enumerate(zip(srt_files, tts_files)),
            )
        )
    )
    units.sort(key=lambda s: s.subtitle.start)
    if word_filter:
        units = list(
            filter(lambda unit: word_filter.is_exclude(unit.subtitle.content), units)
        )
    time_length = units[-1].subtitle.end
    return SpeakerCompose(units, time_length)


def write_srt_with_meta(
    srt_path: Path,
    meta_data: Any = "",
    output_path: Optional[Path] = None,
    encoding="UTF-8",
) -> Path:
    """
    既存のsrtファイルにmetaデータを一律で設定して再度書き込む
    :param srt_path:
    :param meta_data:
    :param output_path:
    :param encoding:
    :return:
    """
    subtitles = list(srt.parse(srt_path.read_text(encoding=encoding)))
    for s in subtitles:
        s.proprietary = str(meta_data)
    output_path = output_path if output_path else srt_path

    output_path.write_text(srt.compose(subtitles), encoding=encoding)
    return output_path
