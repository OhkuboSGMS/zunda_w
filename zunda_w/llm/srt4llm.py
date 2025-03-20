from typing import List, Sequence

from srt import Subtitle

tbl = {2: "A", 3: "B"}


def srt4llm(srt: Sequence[Subtitle]):
    """srtの中身をllmで読みやすい形に変換する"""
    txt = list(
        map(lambda x: f'[{tbl[int(x.proprietary)]}{x.index}] {x.content}', srt))

    # 変換したテキストをllmに入力できる
    return txt
