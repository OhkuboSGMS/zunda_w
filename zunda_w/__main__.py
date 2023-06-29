import os.path

from loguru import logger

from zunda_w.main import main, Options
from omegaconf import OmegaConf, read_write, SCMode


# CLI部分とOptions部分を切り分け
def cli():
    arg = Options.from_args()
    conf = OmegaConf.structured(arg)

    if conf.preset:
        logger.info('Output config preset to preset.yaml')
        OmegaConf.save(conf, 'preset.yaml')
        return
    if conf.preset_file and os.path.exists(conf.preset_file):
        preset = OmegaConf.load(conf.preset_file)
        conf = OmegaConf.unsafe_merge(conf, preset)
    conf.preset = False
    logger.info('Parameters:')
    logger.info(OmegaConf.to_yaml(conf))
    conf = OmegaConf.to_container(conf,structured_config_mode=SCMode.INSTANTIATE)
    print(conf.clear)
    for msg, data in main(conf):
        logger.debug(msg)
        logger.debug(data)


if __name__ == '__main__':
    cli()
