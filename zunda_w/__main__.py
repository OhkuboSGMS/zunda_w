import sys
from functools import partial

import fire
from loguru import logger
from omegaconf import OmegaConf

from zunda_w.apis import cmd
from zunda_w.etc import cmd_log
from zunda_w.etc.tools import argv_omit
from zunda_w.main import main, Options


def _convert(conf):
    for msg, data in main(conf):
        logger.debug(msg)
        logger.debug(data)


if __name__ == '__main__':
    cmd_log.commit(sys.argv)
    with argv_omit(1):
        arg = Options.from_args()
        conf = OmegaConf.structured(arg)

    fire.Fire({
        'convert': partial(_convert, conf),
        'preset': partial(cmd.create_preset, conf),
        'clear': partial(cmd.clear_cache, arg.data_cache_dir),
        'speaker': partial(cmd.show_speaker, arg.speaker_json, arg.engine_dir),
    })
