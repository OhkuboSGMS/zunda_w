from typing import Dict, List, Sequence

from zunda_w.util import text_hash


def concat_hash(data: Sequence[str]) -> str:
    """
    複数のハッシュ値を結合.

    :param data: ハッシュ済みの整数(元はオブジェクト)
    :return:dataを結合後のハッシュ値
    """
    return text_hash(''.join(sorted(map(str, data))).encode())


def dict_hash(data: Dict) -> str:
    return ''.join((map(lambda x: str(x[0]) + str(x[1]), (sorted(data.items())))))
