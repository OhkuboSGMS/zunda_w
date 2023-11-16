from zunda_w.util import read_srt, write_srt


def dummy(srt_file: str) -> str:
    srts = read_srt(srt_file)
    for srt in srts:
        srt.content = srt.content + "_Dummy"
    write_srt(srt_file, srts)
    return srt_file
