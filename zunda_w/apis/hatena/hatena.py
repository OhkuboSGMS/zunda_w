import os
from datetime import datetime
from pathlib import Path
from typing import Tuple, Sequence, Optional

import requests as req

BASE_URL = "https://blog.hatena.ne.jp/{}/{}/atom"

TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "hatena_blog_post_template.xml")

from loguru import logger


def _as_category_tag(categories: Sequence) -> str:
    return "\n".join([f"<category term='{e}'/>" for e in categories])


def escape_xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def post_blog(title: str, content: str, categories=(), updated: str = "", draft: bool = False,
              template_file: str = TEMPLATE_FILE,
              custom_url: Optional[str] = None) -> Tuple[int, Optional[str]]:
    """
    Hateba blog post APIを使って、はてなブログに投稿する
    https://developer.hatena.ne.jp/ja/documents/blog/apis/atom#%E3%83%96%E3%83%AD%E3%82%B0%E3%82%A8%E3%83%B3%E3%83%88%E3%83%AA%E3%81%AE%E6%8A%95%E7%A8%BF

    :param title: 記事タイトル
    :param content: 記事本文 形式はmarkdown
    :param categories: 記事に付与するカテゴリ(最大数は不明)
    :param updated:更新日時(フォーマット: 2021-08-01T00:00:00)
    :param draft: 下書きの場合はTrue
    :param template_file: XMLテンプレートファイル
    :return:status_code, posted_url
    """
    if any(map(lambda x: x not in os.environ, ["HATENA_ID", "HATENA_API_KEY", "HATENA_BLOG_DOMAIN"])):
        raise ValueError("Please set environment variables, HATENA_ID, HATENA_API_KEY and HATENA_BLOG_DOMAIN")
    HATENA_ID, API_KEY, BLOG_DOMAIN = os.environ["HATENA_ID"], os.environ["HATENA_API_KEY"], os.environ[
        "HATENA_BLOG_DOMAIN"]

    if not os.path.exists(template_file):
        raise FileNotFoundError(f"Template file not found: {template_file}")

    url = BASE_URL.format(HATENA_ID, BLOG_DOMAIN)
    template = Path(template_file).read_text(encoding="utf-8")
    updated = updated if updated else datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    draft = "yes" if draft else "no"
    categories = _as_category_tag(categories) if categories else ""
    custom_url = custom_url if custom_url else datetime.now().strftime("%Y-%m-%d")
    content = escape_xml(content)
    xml = template.format(title=title, content=content, updated=updated, draft=draft, categories=categories,
                          blog_url=custom_url)
    xml_bytes = xml.encode("utf-8")
    r = req.post(f"{url}/entry", auth=(HATENA_ID, API_KEY), data=xml_bytes)
    logger.debug(f"[はてなブログ] Posted to {url}/entry:{r.content.decode()}")
    return r.status_code, r.headers.get("Location", default=None)
