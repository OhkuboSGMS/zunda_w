import asyncio
from asyncio import sleep
from typing import Optional

from loguru import logger

from zunda_w.apis import blue_sky, twitter
from zunda_w.apis import hatena
from zunda_w.apis.blue_sky import get_og_tags


async def share(url: str, retry: int = 3,
                blog_template: Optional[str] = None,
                blog_template_kwargs: Optional[dict] = None, draft: bool = False) -> dict:
    if blog_template_kwargs is None:
        blog_template_kwargs = {}

    result = {}
    n_retry = 0
    title = "test-title"
    while n_retry < retry:
        try:
            image_url, title, description = get_og_tags(url)
            break
        except Exception as e:
            logger.exception(e)
            logger.info(f"Retry get og tags: {n_retry} times")
            n_retry += 1
            await sleep(1)
            continue
    if url:
        # blueskyで共有
        result["blue_sky"] = blue_sky.post_card(url)
        logger.info(f"Blue Skyに投稿しました:{result['blue_sky']}")
        # Xで共有
        result["twitter"] = twitter.tweet(title, url)
        logger.info(f"Twitterに投稿しました:{result['twitter']}")

        # はてなブログに投稿
        """
        埋める必要がある値
        podcast_url,        
        episode_number,
        show_note,
        transcript,
        """
        logger.info("はてなブログに投稿します")
        blog_kwargs = {"podcast_url": url,
                       "title": blog_template_kwargs["blog_title"],
                       **blog_template_kwargs}
        post_markdown: str = hatena.render_from_file(blog_template, blog_kwargs)
        status, url = hatena.post_blog(title, post_markdown, blog_kwargs["categories"], draft=draft)
        result["hatena_md"] = post_markdown
        result["hatena_url"] = url
        result["hatena_status"] = status

    return result


if __name__ == '__main__':
    _url = "<podcast_url>"
    result = asyncio.run(share(_url, retry=10, blog_template="config/markdown/blog_template.md",
                               blog_template_kwargs={"episode_number": 101, "categories": ["ポッドキャスト"],
                                                     "show_note": "This is a show note",
                                                     "transcript": "This is a transcript"}
                               )
                         )
    logger.info(result)
