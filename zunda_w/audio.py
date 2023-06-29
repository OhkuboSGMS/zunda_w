from typing import Iterator

from pydub import AudioSegment


def concatenate(segment: Iterator[AudioSegment]) -> AudioSegment:
    """
    AudioSegmentを結合.
    時間は全体の長さになる
    :param segment:
    :return:
    """
    empty = AudioSegment.empty()
    for audio in segment:
        empty += audio
    return empty


def concatenate_from_file(wav_files: Iterator[str]) -> AudioSegment:
    """
    音声ファイルを順番に結合
    """
    return concatenate(map(AudioSegment.from_file, wav_files))