from zunda_w.postprocess.srt import tag


def test_any_tag():
    a = "[next]"
    assert print(tag.contain_any_tag(a))


def test_contain_tag():
    a = "[next]"
    result = tag.contain_tag(a, "[next]")
    assert result