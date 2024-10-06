import re
from typing import Tuple, List

pattern = re.compile(r'\[(.*?)\]')


def extract_text(text: str) -> str:
    return pattern.sub('', text)


def extract_tag_key(text: str) -> List[str]:
    return list(map(lambda x: x[1], extract_tag(text)))


def extract_tag(text: str) -> List[Tuple[Tuple[int, int], str]]:
    """
    テキストからタグを抽出．タグは'[XXX]'として[]付きで抽出
    :param text:
    :return:
    """
    result = []
    for m in re.finditer(pattern, text):
        start, end, tag = m.start(), m.end(), m.group(0)
        result.append(((start, end), tag[1:-1]))
    return result


def contain_any_tag(text: str) -> bool:
    return len(extract_tag(text)) > 0


def contain_tag(text: str, tag: str) -> bool:
    result = extract_tag(text)
    if len(result) == 0:
        return False
    return len(list(filter(lambda x: x[1] == tag, result))) > 0


def contain_tag_in_tag_list(check_tag: List[str], tag_list: List[str]) -> bool:
    """
    tag_listの中のどれかがcheck_tagに含まれているかチェック
    :param check_tag:
    :param tag_list:
    :return:
    """
    return any(map(lambda x: x in tag_list, check_tag))


def as_tag(text: str):
    return "[" + text + "]"
