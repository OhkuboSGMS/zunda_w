import json
import os
from pathlib import Path
from typing import List, Iterator, Any, Optional, Tuple

from classopt import classopt, config
from loguru import logger

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
    audio_files: List[str] = config(long=False, short=False, nargs='+', type=str)
    output: str = 'arrange.wav'
    speakers: List[int] = DEFAULT_SPEAKER_IDs
    default_profile: WhisperProfile = WhisperProfile()
    profile_json: str = 'profile_json'
    default_v_profile: VoiceVoxProfile = VoiceVoxProfile()
    v_profile_json: str = 'v_profile.json'
    speaker_json: str = 'speakers.json'
    word_filter: str = 'filter_word.txt'
    no_detect_silence: bool = False
    cache_root_dir: str = os.curdir
    data_cache_dir: str = '.cache'
    engine_cache_dir: str = cache.user_cache_dir('voicevox')

    ostt: bool = False
    otts: bool = False
    show_speaker: bool = False

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


def main(arg: Options) -> Iterator[Tuple[str, Optional[Any]]]:
    voicevox_process = None
    cache_tts = '.tts'
    logger.success('start process')
    if arg.audio_files is None:
        raise Exception('Pass Audios Files')
    try:
        # voicevox立ち上げ,フォルダが無ければダウンロードする.
        voicevox_process = voice_vox.launch_voicevox_engine(voice_vox.extract_engine(root_dir=arg.engine_dir))
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
        voicevox_profiles = arg.voicevox_profiles(len(audio_files))
        word_filter = WordFilter(arg.word_filter)
        stt_files = []
        tts_dirs = []
        for idx, (original_audio, speaker_id) in enumerate(zip(audio_files, speakers)):
            audio_hash = file_hash(original_audio)
            cache_dir = os.path.join(arg.data_dir, audio_hash)
            logger.debug('speech to text')
            # オリジナル音声の用意
            if arg.no_detect_silence:
                stt_file = list(transcribe_with_config([original_audio], whisper_profile, root_dir=cache_dir))[0]
            # オリジナル音声の無音区間を切り抜き
            else:
                # Tuple[meta],Tuple[audio]
                meta, silent_audio = silent.divide_by_silence(original_audio, root_dir=cache_dir)
                # 切り抜き音声から文字おこし
                stt_file = transcribe_non_silence_srt(silent_audio, meta, whisper_profile, cache_dir)
            yield 'Speech to Text(Whisper)', stt_file
            logger.debug('text to speech')
            # voicevoxによる音声合成
            logger.debug(f'{stt_file} to {voice_vox.get_speaker_info(speaker_id, speakers_data)}')
            tts_dir = voice_vox.run(stt_file, speaker=speaker_id, root_dir=cache_dir, output_dir=cache_tts,
                                    query=voicevox_profiles[idx])

            stt_files.append(stt_file)
            tts_dirs.append(tts_dir)
            yield 'Text to Speech(Voicevox)', tts_dir
        # srt,audioのソート
        logger.debug('sort srt and audio')
        # 相槌をある程度フィルタリングする
        compose: SpeakerCompose = merge(stt_files, tts_dirs, word_filter=word_filter)
        yield 'Merge Audio Files', compose
        # 音声は位置
        logger.debug('arrange audio')
        arrange_sound = edit.arrange(compose)
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
