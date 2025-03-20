import re
from pathlib import Path
from typing import Sequence

import srt

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage
from loguru import logger
from zunda_w.postprocess.srt import tag


def contains_alphabet(text) -> bool:
    return bool(re.search(r"[a-zA-Z]", text))


# https://platform.openai.com/playground/p/KxUoo02lAi0vyTZwW4sIfB13?model=gpt-4

MODEL_NAME = "gpt-4o"


def word_to_kana(srt_file: str) -> str:
    """
    ChatGPTを使って英単語をカナに変換．
    API仕様にあたって，料金が発生するため，英文字が存在しているセンテンスに限定して，処理を行う．
    :param srt_file:
    :return:
    """
    logger.debug("Convert English word to カナ with ChatGPT API.")
    srts: Sequence[srt.Subtitle] = list(srt.parse(Path(srt_file).read_text()))
    chat = ChatOpenAI(temperature=0, model_name=MODEL_NAME)
    chat_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content="Please convert the English words that appear in the sentence into katakana.\n\n\n# Example\n\n#Input\nそういうWebアプリがありまして、何でこれを探してた、\n\n#Output\nそういうウェブアプリがありまして、何でこれを探してた、\n\n"
            ),
            HumanMessagePromptTemplate.from_template("# Input\n{input}\n\n#Output"),
        ]
    )
    target_subtitles = list(
        filter(lambda stt: contains_alphabet(stt.content) and not tag.contain_any_tag(stt.content), srts))
    for s in target_subtitles:
        s.content = chat(
            chat_prompt.format_prompt(input=s.content).to_messages()
        ).content
    Path(srt_file).write_text(srt.compose(srts, reindex=False))
    return srt_file
