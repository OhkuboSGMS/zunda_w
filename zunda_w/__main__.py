import sys

import fire
from loguru import logger
from omegaconf import OmegaConf

from zunda_w.apis import cmd
from zunda_w.etc import cmd_log
from zunda_w.etc.tools import argv_omit, partial_doc
from zunda_w.main import Options, main


def _convert(conf, *args, **kwargs):
    """
    音声ファイルの変換
    :param conf:
    :param args:
    :param kwargs:
    :return:
    """
    for msg, data in main(conf):
        logger.debug(msg)


#        logger.debug(data)


def _main():
    cmd_log.commit(sys.argv)
    with argv_omit(1):
        # TODO  --helpでOptionのhelpが出てしまうので修正
        # TODO OptionのインスタンスとOmegaconf.from_cli()を融合すればよさそう
        arg = Options.from_args()
        conf = OmegaConf.structured(arg)

    fire.Fire(
        {
            "convert": partial_doc(_convert, conf),
            "preset": partial_doc(cmd.create_preset, conf),
            "clear": partial_doc(cmd.clear_cache, arg.data_cache_dir),
            "speaker": partial_doc(cmd.show_speaker, arg.speaker_json, arg.engine_dir),
            "sample_voice": partial_doc(
                cmd.create_sample_voices, text=arg.text, engine_dir=arg.engine_dir
            ),
        }
    )


if __name__ == "__main__":
    _main()
