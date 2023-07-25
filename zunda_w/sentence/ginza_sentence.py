import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import spacy
import srt
from loguru import logger

GINZA_MODEL = "ja_ginza_electra"


@dataclass
class GinzaSentence:
    n_divide_char: int = 12
    min_char: int = 10

    def reconstruct(
        self, srt_file: str, output: Optional[str] = None, encoding="utf-8"
    ) -> str:
        return _reconstruct(
            srt_file, self.n_divide_char, self.min_char, output, encoding
        )


def _reconstruct(
    srt_file: str,
    n_divide_char=12,
    min_char: int = 10,
    output: Optional[str] = None,
    encoding="utf-8",
) -> str:
    """
    文章が一定以上長いものをginzaから文章を解析して分割する
    srt -> srt
    """
    logger.debug("Reconstruct with GinZa")
    subtitles = list(srt.parse(Path(srt_file).read_text(encoding=encoding)))
    nlp = spacy.load(GINZA_MODEL)
    re_subtitles = []
    for sub in subtitles:
        doc = nlp(sub.content)
        reconstructs = []
        tmp = []
        tag_group = ["助詞-接続助詞", "助詞-終助詞"]
        for sent in doc.sents:
            for token in sent:
                if token.tag_ in tag_group and len(tmp) >= n_divide_char:
                    tmp.append(token.orth_)
                    reconstructs.append("".join(tmp))
                    tmp.clear()
                else:
                    tmp.append(token.orth_)
        # 残った文字がmin_charより大きければ
        # 独立したセンテンスとする
        # min_charより小さければ，最後のセンテンスにまとめる.
        if len(tmp) > min_char:
            reconstructs.append("".join(tmp))
        else:
            if len(reconstructs) > 0:
                reconstructs[-1] += "".join(tmp)
            else:
                reconstructs.append("".join(tmp))
        for sent in reconstructs:
            sent_sub = copy.copy(sub)
            sent_sub.content = sent
            re_subtitles.append(sent_sub)

    path = Path(output) if output else Path(srt_file)
    path.write_text(srt.compose(re_subtitles), encoding=encoding)
    return str(path)
