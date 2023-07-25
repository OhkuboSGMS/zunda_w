import json
import os
from datetime import timedelta
from pathlib import Path
from typing import List, Tuple

import openai
import srt
from loguru import logger

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.warning("OPENAI_API_KEY not found. need key for OPENAI api use")


def save(file_name: str, response):
    """
    openai response結果をファイルに保存する
    :param file_name:
    :param response:
    :return:
    """
    try:
        print(response["choices"][0]["message"]["content"])
    except Exception as e:
        print(e)
    with open(file_name, "w", encoding="UTF-8") as fp:
        json.dump(response, fp, ensure_ascii=False)


def run(q: str, prompt: str = "あなたは与えられた用語に関して解説します。") -> Tuple[str, str]:
    request = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": q},
    ]
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=request)
    save(request[-1]["content"] + ".json", response)
    return request[-1]["content"] + ".json", response


def response_as_srt(response) -> List[srt.Subtitle]:
    message: str = response["choices"][0]["message"]["content"]
    srt_list = []
    for idx, msg in enumerate(message.split("\n")):
        srt_list.append(
            srt.Subtitle(
                index=None,
                start=timedelta(seconds=idx),
                end=timedelta(seconds=idx + 1),
                content=msg,
            )
        )

    return list(filter(lambda x: x.content != "", srt_list))


if __name__ == "__main__":
    j = json.loads(Path("test.json").read_text(encoding="UTF-8"))
    response_as_srt(j)
