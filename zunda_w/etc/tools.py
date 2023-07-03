import contextlib
import sys


@contextlib.contextmanager
def argv_omit(index: int):
    _tmp = sys.argv.pop(index) if len(sys.argv) > index else None
    yield
    if _tmp:
        sys.argv.insert(index, _tmp)