import dataclasses
import json
import os
import shutil
from functools import cached_property
from pathlib import Path
from typing import List, Iterator, Any, Optional, Tuple

import srt
from classopt import classopt
from loguru import logger
from pydub import AudioSegment

from zunda_w import download_voicevox
from zunda_w import edit, silent, voice_vox, transcribe_non_silence_srt, transcribe_with_config, file_hash, \
    SpeakerCompose, merge, array_util, cache
from zunda_w.util import try_json_parse
from zunda_w.voice_vox import VoiceVoxProfile, VoiceVoxProfiles
from zunda_w.whisper_json import WhisperProfile
from zunda_w.words import WordFilter

# 東北(ノーマル) ,四国(ノーマル),埼玉(ノーマル),九州(ノーマル)
DEFAULT_SPEAKER_IDs = [3, 2, 8, 16]


@classopt(default_long=True)
class Options:
    # 文字起こしする音声ファイル
    audio_files: List[str] = []
    # 既存のsrtファイル audio_filesと二者択一
    srt_file: Optional[str] = None
    output: str = 'arrange.wav'
    speakers: List[int] = DEFAULT_SPEAKER_IDs
    default_profile: WhisperProfile = WhisperProfile()
    profile_json: str = 'profile.json'
    default_v_profile: VoiceVoxProfile = VoiceVoxProfile()
    v_profile_json: str = 'v_profile.json'
    speaker_json: str = 'speakers.json'
    word_filter: str = 'filter_word.txt'
    prompt: str = 'prompt.txt'
    no_detect_silence: bool = False
    cache_root_dir: str = os.curdir
    data_cache_dir: str = '.cache'
    engine_cache_dir: str = cache.user_cache_dir('voicevox')

    ostt: bool = False
    otts: bool = False
    show_speaker: bool = False
    playback: bool = False
    # clear cache (dont run script)
    clear: bool = False

    @property
    def data_dir(self) -> str:
        return os.path.join(self.cache_root_dir, self.data_cache_dir)

    @property
    def engine_dir(self) -> str:
        return os.path.join(self.cache_root_dir, self.engine_cache_dir)

    @property
    def whisper_profile(self) -> WhisperProfile:
        if self.profile_json and os.path.exists(self.profile_json) and try_json_parse(self.profile_json):
            return WhisperProfile.from_json(Path(self.profile_json).read_text(encoding='UTF-8'))
        else:
            return self.default_profile

    def voicevox_profiles(self, n: int) -> VoiceVoxProfiles:
        if self.v_profile_json and os.path.exists(self.v_profile_json) and try_json_parse(self.v_profile_json):
            profile = json.loads(Path(self.v_profile_json).read_text(encoding='UTF-8'))
            return list(array_util.duplicate_last(profile, n))
        else:
            return [self.default_v_profile for i in range(n)]

    @cached_property
    def prompt_text(self) -> str:
        return Path(self.prompt).read_text(encoding='UTF-8')


def main(arg: Options) -> Iterator[Tuple[str, Optional[Any]]]:
    voicevox_process = None
    cache_tts = '.tts'
    logger.success('start process')
    if arg.clear:
        logger.info(f'Clear Cache Files @{arg.data_cache_dir}')
        shutil.rmtree(arg.data_cache_dir, ignore_errors=True)
        return
    if arg.audio_files is None:
        raise Exception('Pass Audios Files')
    try:
        # voicevox立ち上げ,フォルダが無ければダウンロードする.
        voicevox_process = voice_vox.launch_voicevox_engine(download_voicevox.extract_engine(root_dir=arg.engine_dir))
        voice_vox.wait_until_voicevox_ready()
        yield 'Launch Voicevox', None

        if not os.path.exists(arg.speaker_json):
            voice_vox.get_speakers(arg.speaker_json)

        # 現在のvoicevoxの実装済み話者を取得
        if arg.show_speaker:
            if speakers := voice_vox.get_speakers(arg.speaker_json):
                logger.info(speakers)
            else:
                logger.warning('Can\'t get /speakers requests')
            return

        speakers_data = json.loads(Path(arg.speaker_json).read_text(encoding='UTF-8'))
        audio_files = arg.audio_files
        speakers = arg.speakers
        whisper_profile = arg.whisper_profile
        whisper_profile = dataclasses.replace(whisper_profile, prompt=arg.prompt_text)
        logger.debug(f'Prompt:: {whisper_profile.prompt}')
        voicevox_profiles = arg.voicevox_profiles(len(audio_files))
        word_filter = WordFilter(arg.word_filter)
        stt_files = []
        tts_file_list: List[List[str]] = []
        for idx, (original_audio, speaker_id) in enumerate(zip(audio_files, speakers)):
            audio_hash = file_hash(original_audio)
            cache_dir = os.path.join(arg.data_dir, audio_hash)
            logger.debug('speech to text')
            # オリジナル音声の用意
            if arg.no_detect_silence:
                # 文字起こし
                stt_file = list(transcribe_with_config([original_audio], whisper_profile,
                                                       root_dir=cache_dir,
                                                       meta_data=str(speaker_id)
                                                       ))[0]
            # オリジナル音声の無音区間を切り抜き
            else:
                # Tuple[meta],Tuple[audio]
                meta, silent_audio = silent.divide_by_silence(original_audio, root_dir=cache_dir)
                # 切り抜き音声から文字おこし
                stt_file = transcribe_non_silence_srt(silent_audio, meta, whisper_profile, cache_dir,
                                                      meta_data=str(speaker_id))
            yield 'Speech to Text(Whisper)', stt_file
            logger.debug('text to speech')
            # voicevoxによる音声合成
            logger.debug(f'{stt_file} to {voice_vox.get_speaker_info(speaker_id, speakers_data)}')
            tts_files = voice_vox.run(stt_file, speaker=speaker_id, root_dir=cache_dir, output_dir=cache_tts,
                                      query=voicevox_profiles[idx])

            stt_files.append(stt_file)
            tts_file_list.append(tts_files)
            yield 'Text to Speech(Voicevox)', tts_files

        # srt,audioのソート
        logger.debug('sort srt and audio')
        # 相槌をある程度フィルタリングする
        compose: SpeakerCompose = merge(stt_files, tts_file_list, word_filter=word_filter)
        yield 'Merge Audio Files', compose
        if arg.playback:
            logger.debug('playback sort audio')
            compose.playback()
        # 音声は位置
        logger.debug('arrange audio')
        logger.debug(f'export arrange srt to \'{Path(arg.output).with_suffix(".srt")}')
        Path(arg.output).with_suffix('.srt').write_text(srt.compose(compose.srt, reindex=False), encoding='UTF-8')
        arrange_sound: AudioSegment = edit.arrange(compose)
        logger.debug(f'export arrange audio to \'{arg.output}\'')
        arrange_sound.export(arg.output)
        logger.success('finish process')
        yield 'Finish', arg.output
    except Exception as e:
        logger.exception(e)
    finally:
        if voicevox_process is not None:
            voicevox_process.terminate()
            voicevox_process.poll()
