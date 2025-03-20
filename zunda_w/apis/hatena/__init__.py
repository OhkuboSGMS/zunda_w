import os
from pathlib import Path
from typing import *

from .hatena import post_blog
from zunda_w.util import read_preset
from zunda_w.srt_ops import srt_as_interview_blog_content


def generate_interview_blog(srt_file: str, preset_file: str,
                            template_file: str = "zunda_w/apis/hatena/hatena_comment_with_avatar.html",
                            output_file: str = "blog_interview.html"):
    srt_content = Path(srt_file).read_text(encoding="UTF-8")
    parent_dir, file_name = str(Path(preset_file).parent), str(Path(preset_file).stem)
    publish_conf = read_preset(file_name, parent_dir)
    stt_label_map: List[Dict] = publish_conf["speak"]["labels"]
    label_name_map: Dict[str, str] = {e["id"]: e["name"] for e in stt_label_map}
    publish_map: Dict[str, Dict] = {e["id"]: e for e in stt_label_map}
    result: str = srt_as_interview_blog_content(srt_content, template_file, label_name_map, publish_map)

    output_file = Path(output_file)
    output_file.write_text(result, encoding="utf-8")
    return output_file
