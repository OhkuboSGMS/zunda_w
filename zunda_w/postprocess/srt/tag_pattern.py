# このタグが存在する行はそのタグだけで完結する
from functools import partial
from typing import List

SPAN_TAG = ["next"]
PREFIX_TAG = ["e"]
TAGS = [*SPAN_TAG, *PREFIX_TAG]


def is_tag(text: str, target: str):
    return text.startswith(target)


def has_tag(tags: List[str], target: str) -> bool:
    return len(list(filter(partial(is_tag, target=target), tags))) > 0


def get_tag(tags: List[str], target: str):
    return list(map(lambda x: x.replace(target, ""), filter(partial(is_tag, target=target), tags)))[0]



