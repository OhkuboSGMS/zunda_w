import dataclasses
import json
import os
from functools import cached_property
from pathlib import Path
from typing import Any, Iterator, List, Optional, Tuple

from classopt import classopt
from loguru import logger
from omegaconf import OmegaConf, SCMode
from pydub import AudioSegment

from zunda_w import SpeakerCompose, array_util, cache, edit, file_hash, merge, silent
from zunda_w.audio import concatenate_from_file
from zunda_w.etc import alert
from zunda_w.output import OutputDir
from zunda_w.postprocess.srt import postprocess as srt_postprocess
from zunda_w.sentence.ginza_sentence import GinzaSentence
from zunda_w.util import display_file_uri, file_uri, try_json_parse, write_srt
from zunda_w.voicevox import download_voicevox, voice_vox
from zunda_w.voicevox.voice_vox import VoiceVoxProfile, VoiceVoxProfiles
from zunda_w.whisper_json import (
    WhisperProfile,
    clean_model,
    transcribe_non_silence_srt,
    transcribe_with_config,
    whisper_context,
)
from zunda_w.words import WordFilter

# 東北(ノーマル) ,四国(ノーマル),埼玉(ノーマル),九州(ノーマル)
DEFAULT_SPEAKER_IDs = [3, 2, 8, 16]


@classopt(default_long=True)
class Options:
    # 文字起こしする音声ファイル
    audio_files: List[str] = []
    # 合成後の音声の前にくっつける音声ファイル
    prev_files: List[str] = []
    # 合成後の音声の後にくっつける音声ファイル
    next_files: List[str] = []
    # 既存のsrtファイル audio_filesと二者択一
    srt_file: Optional[str] = None
    output_dir: str = "output"
    output: str = "arrange.wav"
    mix_output: str = "mix.wav"
    speakers: List[int] = DEFAULT_SPEAKER_IDs
    default_profile: WhisperProfile = WhisperProfile()
    profile_json: str = "profile.json"
    default_v_profile: VoiceVoxProfile = VoiceVoxProfile()
    v_profile_json: str = "v_profile.json"
    speaker_json: str = "speakers.json"
    word_filter: str = "filter_word.txt"
    prompt: str = "prompt.txt"
    user_dict: str = "user_dict.csv"
    no_detect_silence: bool = True
    cache_root_dir: str = os.curdir
    data_cache_dir: str = ".cache"
    engine_cache_dir: str = cache.user_cache_dir("voicevox")
    preset_file: str = "preset_config/default.yaml"
    ginza: GinzaSentence = GinzaSentence()
    post_processes: List[str] = []
    text: str = "これはサンプルボイスです"
    ostt: bool = False
    otts: bool = False
    playback: bool = False

    @cached_property
    def tool_output(self) -> OutputDir:
        return OutputDir(parent=self.output_dir)

    @property
    def data_dir(self) -> str:
        return os.path.join(self.cache_root_dir, self.data_cache_dir)

    @property
    def engine_dir(self) -> str:
        return os.path.join(self.cache_root_dir, self.engine_cache_dir)

    @property
    def whisper_profile(self) -> WhisperProfile:
        if (
                self.profile_json
                and os.path.exists(self.profile_json)
                and try_json_parse(self.profile_json)
        ):
            return WhisperProfile.from_json(
                Path(self.profile_json).read_text(encoding="UTF-8")
            )
        else:
            return self.default_profile

    def voicevox_profiles(self, n: int) -> VoiceVoxProfiles:
        if (
                self.v_profile_json
                and os.path.exists(self.v_profile_json)
                and try_json_parse(self.v_profile_json)
        ):
            profile = json.loads(Path(self.v_profile_json).read_text(encoding="UTF-8"))
            return list(array_util.duplicate_last(profile, n))
        else:
            return [self.default_v_profile for i in range(n)]

    @cached_property
    def prompt_text(self) -> str:
        return Path(self.prompt).read_text(encoding="UTF-8")


def main(arg: Options) -> Iterator[Tuple[str, Optional[Any]]]:
    if arg.preset_file and os.path.exists(arg.preset_file):
        preset = OmegaConf.load(arg.preset_file)
        arg = OmegaConf.unsafe_merge(arg, preset)

    logger.info("Parameters:")
    logger.info(OmegaConf.to_yaml(arg))
    arg = OmegaConf.to_container(arg, structured_config_mode=SCMode.INSTANTIATE)
    voicevox_process = None
    cache_tts = ".tts"
    cache_general_vv = ".cache/.voicevox"
    audio_files = arg.audio_files
    speakers = arg.speakers
    whisper_profile = arg.whisper_profile
    whisper_profile = dataclasses.replace(whisper_profile, prompt=arg.prompt_text)
    logger.debug(f"Prompt:: {whisper_profile.prompt}")
    voicevox_profiles = arg.voicevox_profiles(len(audio_files))
    if arg.audio_files is None:
        raise Exception("Pass Audios Files")
    # まずspeech to textを行う,ファイルが既に文字お越し済みであれば，そのままファイルを返す
    stt_files = []
    audio_hashes = []

    # speech to text
    with whisper_context():
        for idx, (original_audio, speaker_id) in enumerate(zip(audio_files, speakers)):
            audio_hash = file_hash(original_audio)
            cache_dir = os.path.join(arg.data_dir, audio_hash)
            logger.debug("speech to text")
            post_process: bool = False
            # srtファイルをそのまま返す
            if Path(original_audio).suffix == ".srt":
                logger.debug("Skip Speech to Text : it's srt file")
                stt_file = original_audio

            # オリジナル音声の用意
            elif arg.no_detect_silence:
                # 文字起こし
                stt_file = list(
                    transcribe_with_config(
                        [original_audio],
                        whisper_profile,
                        root_dir=cache_dir,
                        meta_data=str(speaker_id),
                    )
                )[0]
                post_process = True
            # オリジナル音声の無音区間を切り抜き
            else:
                # Tuple[meta],Tuple[audio]
                meta, silent_audio = silent.divide_by_silence(
                    original_audio, root_dir=cache_dir
                )
                # 切り抜き音声から文字おこし
                stt_file = transcribe_non_silence_srt(
                    silent_audio,
                    meta,
                    whisper_profile,
                    cache_dir,
                    meta_data=str(speaker_id),
                )
                post_process = True
            if post_process:
                stt_file = arg.ginza.reconstruct(stt_file, encoding="utf-8")

            srt_postprocess.post_process(stt_file, arg.post_processes)
            stt_files.append(stt_file)
            audio_hashes.append(audio_hash)

    word_filter = WordFilter(arg.word_filter)
    # text to speech
    with voice_vox.voicevox_engine(
            download_voicevox.extract_engine(root_dir=arg.engine_dir)
    ):
        # textファイルを speechする
        voice_vox.import_word_csv(arg.user_dict)
        speakers_data = json.loads(Path(arg.speaker_json).read_text(encoding="UTF-8"))
        tts_file_list: List[List[str]] = []

        for idx, (stt_file, audio_hash) in enumerate(zip(stt_files, audio_hashes)):
            logger.debug(f"text to speech {stt_file}")
            # voicevoxによる音声合成
            cache_dir = os.path.join(arg.data_dir, audio_hash)
            tts_files = voice_vox.run(
                stt_file,
                root_dir=cache_dir,
                output_dir=cache_tts,
                query=voicevox_profiles[idx],
            )
            tts_file_list.append(tts_files)
            yield "Text to Speech(Voicevox)", tts_files

    # srt,audioのソート
    logger.debug("sort srt and audio")
    # 相槌をある程度フィルタリングする
    compose: SpeakerCompose = merge(stt_files, tts_file_list, word_filter=word_filter)
    yield "Merge Audio Files", compose
    if arg.playback:
        logger.debug("playback sort audio")
        compose.playback()
    # 音声は位置
    logger.debug("arrange audio")
    output_srt = Path(arg.tool_output(arg.output)).with_suffix(".srt")
    output_wav = arg.tool_output(arg.output)
    output_mix = arg.tool_output(arg.mix_output)
    logger.debug(f"export arrange srt to '{file_uri(output_srt)}")
    write_srt(output_srt, compose.srt)
    arrange_sound: AudioSegment = edit.arrange(compose)
    logger.debug(f"export arrange audio to '{file_uri(output_wav)}'", end="")
    arrange_sound.export(output_wav)
    logger.success("finish process")
    yield "Finish", arg.output
    if len(arg.prev_files) > 0 or len(arg.next_files) > 0:
        mix_audio: AudioSegment = concatenate_from_file(
            [*arg.prev_files, output_wav, *arg.next_files]
        )
        mix_audio.export(output_mix)
        yield "Mix", output_mix
    alert.alert()
