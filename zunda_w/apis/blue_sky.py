import os
import tempfile
from typing import IO, Union, Tuple

import requests
from atproto import Client, models
from atproto_client.utils import TextBuilder
from bs4 import BeautifulSoup


def get_og_tags(url: str) -> Tuple[str, str, str]:
    """
    Get og:image, og:title, og:description from url
    :param url:
    :return: image url, title, description
    """
    res = requests.get(url)
    html = res.text
    soup = BeautifulSoup(html, 'html.parser')
    og_image = soup.find_all('meta', attrs={'property': 'og:image'})
    og_title = soup.find_all('meta', attrs={'property': 'og:title'})
    og_description = soup.find_all('meta', attrs={'property': 'og:description'})
    if len(og_image) == 0 or len(og_title) == 0 or len(og_description) == 0:
        raise ValueError("No og:image or og:title or og:description found")
    return og_image[0]["content"], og_title[0]["content"], og_description[0]["content"]


def embed_post(client: Client, text: Union[str, TextBuilder], title: str, description: str, url: str,
               image_fp: IO[bytes]):
    thumb_ref = client.upload_blob(image_fp.read())
    # AppBskyEmbedExternal is the same as "link card" in the app
    embed_external = models.AppBskyEmbedExternal.Main(
        external=models.AppBskyEmbedExternal.External(
            title=title,
            description=description,
            uri=url,
            thumb=thumb_ref.blob
        )
    )
    post_with_link_card = client.send_post(text=text, embed=embed_external)
    return post_with_link_card


def post_card(url: str, dry_run: bool = False):
    if url is None:
        raise ValueError("url is None")
    client = Client()
    client.login(os.environ["BLUE_SKY_ID"], os.environ["BLUE_SKY_PASS"])

    with tempfile.TemporaryFile() as img_fp:
        img_url, title, description = get_og_tags(url)
        # Download image from og:image url
        img_fp.write(requests.get(img_url).content)
        img_fp.seek(0)

        text = f"Listen to \"{title}\""
        text_builder = TextBuilder() \
            .text('新しいエピソードが配信されました\n') \
            .text(text) \
            .tag("#ポッドキャスト", "ポッドキャスト") \
            .text(' ') \
            .tag("#とにかくヨシ！", "とにかくヨシ！")
        if dry_run:
            return text_builder.build_text()
        result = embed_post(client, text_builder, title, description, url, img_fp)
    return result
