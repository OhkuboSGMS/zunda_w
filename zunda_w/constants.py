from pathlib import Path

from more_itertools import flatten

DEFAULT_SPEAKER_IDs = [3, 2, 8, 16]
PRESET_NAME = ["default", "postprocess", "movie"]


def list_preset(preset_dir: str, patterns=("*.yaml",)):
    """
    preset_dir配下のyamlファイル名を返す
    :param preset_dir:
    :param patterns: globのパターン
    :return:
    """
    return list(flatten(map(lambda x: map(lambda y: str(y.stem), Path(preset_dir).glob(x)), patterns)))


def update_preset(preset_dir: str):
    """
    preset_dir配下のyamlファイル名でPRESET_NAMEを更新
    :param preset_dir:
    :return:
    """
    global PRESET_NAME
    PRESET_NAME = list_preset(preset_dir)
