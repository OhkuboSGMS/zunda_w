import contextlib
import sys
from functools import partial
from typing import Callable


@contextlib.contextmanager
def argv_omit(index: int):
    _tmp = sys.argv.pop(index) if len(sys.argv) > index else None
    yield
    if _tmp:
        sys.argv.insert(index, _tmp)


def partial_doc(f: Callable, *args, **kwargs):
    partial_f = partial(f, *args, **kwargs)
    partial_f.__doc__ = f.__doc__
    return partial_f
