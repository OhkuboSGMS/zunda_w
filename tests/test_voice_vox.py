from zunda_w.voice_vox import VoiceVoxProfile
from zunda_w.hash import dict_hash, concat_hash
from zunda_w.util import text_hash


def test_profile_hash():
    """
    dictのhash関数を確認.同値性をチェック
    """
    assert dict_hash(VoiceVoxProfile()) == dict_hash(VoiceVoxProfile())
    assert dict_hash(VoiceVoxProfile(speedScale=1.5)) == dict_hash(VoiceVoxProfile(speedScale=1.5))


def test_str_hash():
    """
    strの同値性をチェック
    """
    assert text_hash('User'.encode()) == text_hash('User'.encode())
    assert text_hash('User1'.encode()) != text_hash('User'.encode())


def test_concat_hash():
    """
    複数のhash値を組み合わせた際に再現性を確認
    """
    profile1 = VoiceVoxProfile(speedScale=1.3, pitchScale=1.2)
    profile2 = VoiceVoxProfile(speedScale=1.0)
    text1 = 'こんにちわ'
    text2 = 'さようなら'
    concat_text1_hash = 'a9bff13e3c4b584d80632c7c37ac99ca'
    # 順序性がないことを確認
    assert concat_hash([dict_hash(profile1), text_hash(text1)]) == concat_hash([text_hash(text1), dict_hash(profile1)])
    # concat_hashと元のhashは違う
    assert concat_hash([text_hash(text1)]) != text_hash(text1)
    # 中身が同じデータは一致する
    assert concat_hash([text_hash(text1)]) == concat_hash([text_hash(text1)])
    # 中身が違うデータは一致しない
    assert concat_hash([dict_hash(profile1)]) != concat_hash([dict_hash(profile2)])
    # 3つ以上でも同じ
    assert concat_hash([text_hash(text1), text_hash(text2), dict_hash(profile1)]) \
           == concat_hash([dict_hash(profile1), text_hash(text1), text_hash(text2) ])
    # ランタイムによらず常に同じ値が計算される．
    assert concat_hash([text_hash(text1)]) == concat_text1_hash