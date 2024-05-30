from asyncio import sleep
from typing import Optional

import fire
from loguru import logger

from zunda_w.apis import blue_sky, twitter
from zunda_w.apis.blue_sky import get_og_tags


async def share(url: str, content: Optional[str] = None, retry: int = 3) -> dict:
    result = {}
    n_retry = 0
    title = ""
    while n_retry < retry:
        try:
            image_url, title, description = get_og_tags(url)
        except Exception as e:
            logger.error(e)
            logger.info(f"Retry get og tags: {n_retry} times")
            n_retry += 1
            await sleep(1)
            continue
    if url:
        # blueskyで共有
        result["blue_sky"] = blue_sky.post_card(url)
        logger.info("Blue Skyに投稿しました")
        # TODO はてなブログで共有
        # if content:
        #     code, url = post_blog(title, content, ["AI", "小僧"], haxx)
        #     result["hatena_url"] = url
        # Xで共有
        logger.info("Twitterに投稿しました")
        result["twitter"] = twitter.tweet(title, url)

    return result


def main():
    fire.Fire({
        "share": share,
        "hatena": None
    })


if __name__ == "__main__":
    main()
