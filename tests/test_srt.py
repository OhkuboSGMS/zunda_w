from pathlib import Path

from srt import parse


def test_srt_missing_index_available():
    """
    indexのつながりが無くてもsrtパッケージはOK
    :return:
    """
    result = list(parse(Path('tests/test_data/missing_index.srt').read_text(encoding='UTF-8')))
    assert result[0].index == 1
    assert result[1].index == 2
    assert result[2].index == 5
