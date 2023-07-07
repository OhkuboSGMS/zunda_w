import shutil

from loguru import logger
from omegaconf import OmegaConf

from zunda_w.voicevox import voice_vox, download_voicevox


def clear_cache(cache_dir: str):
    """
    生成された途中ファイルをすべて削除する
    """
    logger.info(f'Clear Cache Files @{cache_dir}')
    return shutil.rmtree(cache_dir, ignore_errors=True)


def create_preset(conf):
    """
    現在の設定をファイルに出力する
    :return:
    """
    logger.info('Output config preset to preset.yaml')
    return OmegaConf.save(conf, 'preset.yaml')


def show_speaker(output_json: str, engine_dir: str):
    """
    voicevoxに内蔵されている話者一覧を表示
    :param output_json:
    :param engine_dir:
    :return:
    """
    with voice_vox.voicevox_engine(download_voicevox.extract_engine(root_dir=engine_dir)):
        # TODO context voicevox
        if speakers := voice_vox.get_speakers(output_json):
            print(voice_vox.format_speaker(speakers))
            # logger.info(speakers)
        else:
            logger.warning('Can\'t get /speakers requests')
