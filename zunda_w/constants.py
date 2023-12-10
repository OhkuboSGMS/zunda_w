from pathlib import Path

DEFAULT_SPEAKER_IDs = [3, 2, 8, 16]
PRESET_NAME = ["default", "postprocess", "movie"]


def update_preset(preset_dir: str):
    """
    preset_dir配下のyamlファイル名でPRESET_NAMEを更新
    :param preset_dir:
    :return:
    """
    global PRESET_NAME
    PRESET_NAME = list(map(lambda x: str(x.stem), Path(preset_dir).glob("*.yaml")))
