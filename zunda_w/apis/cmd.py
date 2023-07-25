import shutil
from pathlib import Path

from loguru import logger
from omegaconf import OmegaConf
from pathvalidate import sanitize_filename

from zunda_w import subtitle_util
from zunda_w.voicevox import download_voicevox, voice_vox


def clear_cache(cache_dir: str):
    """
    生成された途中ファイルをすべて削除する
    """
    logger.info(f"Clear Cache Files @{cache_dir}")
    return shutil.rmtree(cache_dir, ignore_errors=True)


def create_preset(conf):
    """
    現在の設定をファイルに出力する
    :return:
    """
    logger.info("Output config preset to preset.yaml")
    return OmegaConf.save(conf, "preset.yaml")


def show_speaker(output_json: str, engine_dir: str):
    """
    voicevoxに内蔵されている話者一覧を表示
    :param output_json:
    :param engine_dir:
    :return:
    """
    with voice_vox.voicevox_engine(
        download_voicevox.extract_engine(root_dir=engine_dir)
    ):
        if speakers := voice_vox.get_speakers(output_json):
            print(voice_vox.format_speaker(speakers))
        else:
            logger.warning("Can't get /speakers requests")


def create_sample_voices(text: str, engine_dir: str, output: str = "sample_voice"):
    """voicevoxで実装されているキャラクターに同一を読み上げを行わせる
    :param text:
    :param engine_dir:
    :param output:
    :return:
    """
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with voice_vox.voicevox_engine(
        download_voicevox.extract_engine(root_dir=engine_dir)
    ):
        if speakers := voice_vox.get_speakers():
            output_names = []
            request_list = []
            for one_char in speakers:
                name = one_char["name"]
                styles = one_char["styles"]
                for s in styles:
                    file_name = f'{name}({s["name"]})'
                    speaker_id = s["id"]
                    request_list.append(speaker_id)
                    output_names.append(sanitize_filename(file_name))
            subtitles = subtitle_util.from_proprietaries(text, request_list)
            voice_vox.run(
                subtitles,
                root_dir=str(output),
                output_names=output_names,
                output_dir="",
                use_cache=False,
            )
        else:
            logger.warning("Can't get /speakers requests")
