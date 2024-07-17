import json
import os
import shutil
import uuid
from functools import cached_property
from pathlib import Path
from typing import List, Optional

from classopt import classopt

from zunda_w import cache, array_util
from zunda_w.constants import DEFAULT_SPEAKER_IDs
from zunda_w.output import OutputDir
from zunda_w.sentence.ginza_sentence import GinzaSentence
from zunda_w.util import try_json_parse
from zunda_w.voicevox.voice_vox import VoiceVoxProfile, VoiceVoxProfiles
from zunda_w.whisper_json import WhisperProfile


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
    target_dir: Optional[str] = None
    output_dir: str = "output"
    output: str = "arrange.wav"
    mix_output: str = "mix.wav"
    speakers: List[int] = DEFAULT_SPEAKER_IDs
    default_profile: WhisperProfile = WhisperProfile()
    profile_json: str = "profile.json"
    default_v_profile: VoiceVoxProfile = VoiceVoxProfile()
    v_profile_json: str = "v_profile.json"
    speaker_json: str = "speakers.json"
    word_filter: str = "config/filter_word.txt"
    prompt: str = "prompt.txt"
    user_dict: str = "user_dict.csv"
    no_detect_silence: bool = True
    cache_root_dir: str = os.curdir
    data_cache_dir: str = ".cache"
    temp_dir: str = ".tmp"
    engine_cache_dir: str = cache.user_cache_dir("voicevox")
    preset_file: str = "preset_config/default.yaml"
    preset_dir: str = "preset_config"
    preset: str = ""
    ginza: GinzaSentence = GinzaSentence()
    post_processes: List[str] = []
    text: str = "これはサンプルボイスです"
    ostt: bool = False
    otts: bool = False
    playback: bool = False

    @cached_property
    def tool_output(self) -> OutputDir:
        return OutputDir(directory=self.target_dir, parent=self.output_dir)

    @property
    def data_dir(self) -> str:
        return os.path.join(self.cache_root_dir, self.data_cache_dir)

    @property
    def tmp_dir(self) -> str:
        _tmp_dir = os.path.join(self.cache_root_dir, 'tmp')
        Path(_tmp_dir).mkdir(exist_ok=True, parents=True)
        return _tmp_dir

    @property
    def tmp_file(self) -> str:
        return os.path.join(self.tmp_dir, str(uuid.uuid4()))

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

    def close(self):
        shutil.rmtree(self.tmp_dir)
