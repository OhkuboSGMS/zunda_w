from pathlib import Path

import srt

import zunda_w.srt_ops
from zunda_w.srt_ops import write_srt_with_meta


def test_srt_missing_index_available():
    """
    indexのつながりが無くてもsrtパッケージはOK
    :return:
    """
    result = list(
        srt.parse(Path("tests/test_data/missing_index.srt").read_text(encoding="UTF-8"))
    )
    assert result[0].index == 1
    assert result[1].index == 2
    assert result[2].index == 5


def test_update_srt_proprietary():
    src_path = Path("tests/test_data/missing_index.srt")
    tmp_srt = Path(".tmp_srt")
    meta_data = "zunda_mon"
    # update meta data
    write_srt_with_meta(src_path, meta_data, tmp_srt)

    for s in srt.parse(tmp_srt.read_text(encoding="UTF-8")):
        assert s.proprietary == meta_data
    tmp_srt.unlink()


def test_hatena_srt(test_srt_1):
    content = Path(test_srt_1).read_text(encoding="UTF-8")
    print(zunda_w.srt_ops.srt_as_blog_content(content))
