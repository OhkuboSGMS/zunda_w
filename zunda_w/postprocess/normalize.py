from pathlib import Path
from typing import Union

from ffmpeg_normalize import FFmpegNormalize


def ffmpeg_normalize(input: Union[str, Path], output: Union[str, Path]) -> Path:
    normalizer = FFmpegNormalize()
    normalizer.add_media_file(str(input), str(output))
    normalizer.run_normalization()
    return output
