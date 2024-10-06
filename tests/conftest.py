import pytest


@pytest.fixture
def test_srt_1():
    return "test_data/missing_index.srt"


@pytest.fixture
def sample_srt():
    return "test_data/sample.srt"