import datetime
from typing import Sequence

from pydub import AudioSegment
from tqdm import tqdm

from zunda_w.srt_ops import SpeakerCompose, merge


def millisecond(t: datetime.timedelta) -> float:
    return int(t.total_seconds() * 1000 + t.microseconds / 1000.0)


def concatenate(wav_files: Sequence[str]) -> AudioSegment:
    """
    音声ファイルを順番に結合
    """
    empty = AudioSegment.empty()
    for audio in wav_files:
        seg = AudioSegment.from_file(audio)
        empty += seg
    return empty


def arrange(compose: SpeakerCompose) -> AudioSegment:
    ms = millisecond(compose.audio_duration)
    empty = AudioSegment.silent(ms, 44100)
    next_sum = 0
    start_point = []
    zunda_duration = []
    for unit in tqdm(compose.unit, desc='Audio composing', unit='wav'):
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


# 合成音声と元音声の時間を比較 合成音声にスケールを合わせる．
def main():
    # オリジナル音声の用意
    # whisperによる音声検出
    sts_files =['sts/okubo_aligned.wav.srt', 'sts/matt_aligned_denoised.wav.srt']
    # voicevoxによる音声合成
    # srt,audioのソート
    compose = merge(sts_files, root='tts')
    # audios = sorted(Path('tts/okubo_aligned.wav').glob('*.wav'))[:10]
    sound = arrange(compose)
    sound.export('arrange.wav')
    # empty = concatenate()
    # empty.export('merge.wav')
    # sound = AudioSegment.from_file('merge.wav')
    # play(sound)


if __name__ == '__main__':
    main()
