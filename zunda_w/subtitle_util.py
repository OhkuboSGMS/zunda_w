from datetime import timedelta
from typing import Sequence, Any, List

import srt


def from_proprietaries(text: str, proprietaries: Sequence[Any]) -> List[srt.Subtitle]:
    t = timedelta()
    return [srt.Subtitle(i, t, t, text, proprietary=p) for i, p in enumerate(proprietaries)]
