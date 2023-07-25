from typing import Any, Iterator, Sequence


def duplicate_last(array: Sequence[Any], size: int) -> Iterator[Any]:
    """
    arrayを size個のシーケンスに拡張する．
    arrayで列挙する要素がなくなったら，最後の要素を終わりまで返す．
    :param array:
    :param size:
    :return:
    """
    if len(array) == 0:
        raise IndexError(array)
    for i in range(size):
        if i >= len(array):
            yield array[-1]
            continue
        yield array[i]
