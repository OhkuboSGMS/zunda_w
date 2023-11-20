import re
from typing import Optional, Tuple, List

pattern = re.compile(r'\[(.*?)\]')


def extract_tag(text: str) -> List[Tuple[Tuple[int, int], str]]:
    result = []
    for m in re.finditer(pattern, text):
        start, end, tag = m.start(), m.end(), m.group(0)
        result.append(((start, end), tag))
    return result


def contain_any_tag(text: str) -> bool:
    return len(extract_tag(text)) > 0


def contain_tag(text: str, tag: str) -> bool:
    result = extract_tag(text)
    if len(result) == 0:
        return False
    return len(list(filter(lambda x: x[1] == tag, result))) > 0
