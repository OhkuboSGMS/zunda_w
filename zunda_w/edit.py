import copy
import datetime
import itertools
from typing import Dict, List

from pydub import AudioSegment

from zunda_w.srt_ops import SpeakerCompose


def millisecond(t: datetime.timedelta) -> float:
    return int(t.total_seconds() * 1000 + t.microseconds / 1000.0)


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
        if seg is None:
            continue
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


def edit_from_yml(audio_files: List[str], blueprint: Dict) -> AudioSegment:
    """
    予め指定されたyamlファイルから音声を合成する
    :param audio_files:
    :param blueprint:
    :return: 合成した音声ファイルのパス
    """
    components = copy.deepcopy(blueprint["components"])
    placeholders = list(filter(lambda x: "audio_placeholder" in x, components))
    # ファイルをPlaceholderに割り当て
    for var, audio_file in enumerate(audio_files):
        if target := next(filter(lambda x: x["audio_placeholder"]["var"] == var, placeholders)):
            target["audio_placeholder"]["path"] = audio_file
    # ファイルが割り当てられていない場合はエラー
    if any(filter(lambda x: x["audio_placeholder"]["path"] is None, placeholders)):
        raise ValueError("Not all audio files are assigned")
    # indexが同じものをmerge
    for index, group in itertools.groupby(placeholders, key=lambda x: x["audio_placeholder"]["index"]):
        group = list(group)
        if len(group) > 1:
            files = [x["audio_placeholder"]["path"] for x in group]
            sounds = list(map(AudioSegment.from_file, files))
            max_length = max(len(sound) for sound in sounds)
            for i, sound in enumerate(sounds):
                if len(sound) < max_length:
                    sounds[i] += AudioSegment.silent(duration=max_length - len(sound))
            merged = sounds[0]
            for sound in sounds[1:]:
                merged = merged.overlay(sound)
            group[0]["audio_placeholder"]["path"] = merged
            for other in group[1:]:
                other["audio_placeholder"]["path"] = None
        else:
            pass
    # 合成
    export = AudioSegment.empty()
    for component in filter(lambda x: x[list(x.keys())[0]]["path"] is not None, components):
        key = list(component.keys())[0]
        if isinstance(component[key]["path"], str):
            export += AudioSegment.from_file(component[key]["path"])
        elif isinstance(component[key]["path"], AudioSegment):
            export += component[key]["path"]
    return export
