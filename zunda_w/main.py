import dataclasses
import os
import shutil
from pathlib import Path
from typing import Any, Iterator, List, Optional, Tuple

from loguru import logger
from omegaconf import OmegaConf, SCMode
from pydub import AudioSegment

from zunda_w import SpeakerCompose, edit, file_hash, merge, silent
from zunda_w.arg import Options
from zunda_w.audio import concatenate_from_file
from zunda_w.constants import update_preset
from zunda_w.etc import alert
from zunda_w.postprocess.srt import postprocess as srt_postprocess
from zunda_w.srt_ops import sort_srt_files
from zunda_w.util import (
    file_uri,
    write_json,
    write_srt,
)
from zunda_w.voicevox import download_voicevox, voice_vox
from zunda_w.transcribe import (
    transcribe_non_silence_srt,
    transcribe_with_config,
    whisper_context,
)
from zunda_w.words import WordFilter


# 東北(ノーマル) ,四国(ノーマル),埼玉(ノーマル),九州(ノーマル)


def main(arg: Options) -> Iterator[Tuple[str, Optional[Any]]]:
    if arg.preset_file and os.path.exists(arg.preset_file):
        update_preset(arg.preset_dir)
        from zunda_w.constants import PRESET_NAME
        if arg.preset != '' and arg.preset in PRESET_NAME:
            # 指定プリセットを優先
            preset = OmegaConf.load(Path(arg.preset_dir).joinpath(arg.preset).with_suffix('.yaml'))
            arg = OmegaConf.unsafe_merge(arg, preset)
        else:
            preset = OmegaConf.load(arg.preset_file)
            arg = OmegaConf.unsafe_merge(arg, preset)

    logger.info("Parameters:")
    logger.info(OmegaConf.to_yaml(arg))
    arg = OmegaConf.to_container(arg, structured_config_mode=SCMode.INSTANTIATE)
    voicevox_process = None
    cache_tts = ".tts"
    cache_general_vv = ".cache/.voicevox"
    sort_srt: bool = True
    audio_files = arg.audio_files
    speakers = arg.speakers
    whisper_profile = arg.whisper_profile
    whisper_profile = dataclasses.replace(whisper_profile, prompt=arg.prompt_text)
    logger.debug(f"Prompt:: {whisper_profile.prompt}")
    voicevox_profiles = arg.voicevox_profiles(len(audio_files))
    if arg.audio_files is None:
        raise Exception("Pass Audios Files")
    # まずspeech to textを行う,ファイルが既に文字起こし済みであれば，そのままファイルを返す
    plain_stt_files = []
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
                stt_file = shutil.copy(original_audio, arg.tmp_file)
                sort_srt = False
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
                # TODO srt_postprocessに移動
                stt_file = arg.ginza.reconstruct(stt_file, encoding="utf-8")

            if len(arg.post_processes) > 0:
                plain_stt_files.append(shutil.copy(stt_file, arg.tmp_file))
            # １# TODO Postprocessの結果がキャッシュにも反映されているため，キャッシュの値が変わってしまうと中身が毎回同じ結果にならない
            srt_postprocess.post_process(stt_file, arg.post_processes)
            stt_files.append(stt_file)
            audio_hashes.append(audio_hash)

    word_filter = WordFilter(arg.word_filter)
    # text to speech
    with voice_vox.voicevox_engine(
            download_voicevox.extract_engine(root_dir=arg.engine_dir)):
        # textファイルを speechする
        voice_vox.import_word_csv(arg.user_dict)
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
    compose: SpeakerCompose = merge(stt_files, tts_file_list, word_filter=word_filter, sort=sort_srt)
    yield "Merge Audio Files", compose

    # 音声は位置
    logger.debug("arrange audio")
    output_srt = str(Path(arg.tool_output(arg.output)).with_suffix(".srt"))
    output_wav = arg.tool_output(arg.output)
    output_mix = arg.tool_output(arg.mix_output)
    output_compose_json = arg.tool_output("compose.json")
    logger.debug(f"export arrange srt to '{file_uri(output_srt)}")
    write_srt(output_srt, compose.srt)
    # post_processが入った場合はPlainなsrtをsrtファイルに出力
    if len(plain_stt_files) > 0:
        output_prev_srt = arg.tool_output("prev.srt")
        output_prev_compose_json = arg.tool_output("prev_compose.json")
        logger.debug(f'export before post-process srt:{file_uri(output_prev_srt)}')
        psf_compose = sort_srt_files(plain_stt_files, word_filter=word_filter)
        write_srt(output_prev_srt, psf_compose.srt)
        # 後処理前のsttファイルと後処理後のttsファイルを組み合わせてcompose.jsonを作成
        write_json(merge(plain_stt_files, tts_file_list, word_filter=word_filter).to_json(), output_prev_compose_json)
    arrange_sound: AudioSegment = edit.arrange(compose)
    logger.debug(f"export directory {file_uri(str(Path(output_srt).parent))}")
    logger.debug(f"export arrange audio to '{file_uri(output_wav)}'", end="")
    arrange_sound.export(output_wav)
    logger.debug(f"export compose json to {file_uri(output_compose_json)}")
    write_json(compose.to_json(), output_compose_json)
    logger.success("finish process")
    yield "Finish", arg.output
    if len(arg.prev_files) > 0 or len(arg.next_files) > 0:
        mix_audio: AudioSegment = concatenate_from_file(
            [*arg.prev_files, output_wav, *arg.next_files]
        )
        mix_audio.export(output_mix)
        yield "Mix", output_mix
    arg.close()
    if arg.playback:
        logger.debug("playback sort audio")
        compose.playback()
    alert.alert()
