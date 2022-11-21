from loguru import logger

from zunda_w.main import main, Options


# CLI部分とOptions部分を切り分け
def cli():
    arg = Options.from_args()
    logger.info('Parameters:')
    logger.info(arg)
    for msg, data in main(arg):
        print(msg, data)


if __name__ == '__main__':
    cli()
