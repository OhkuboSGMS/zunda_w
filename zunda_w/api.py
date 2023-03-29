import os
from datetime import timedelta
from pathlib import Path
from subprocess import Popen
from typing import List, Union, Optional, Tuple, Sequence

import fire
import srt
from pydub import AudioSegment

from zunda_w import voice_vox, download_voicevox, cache, edit, SpeakerCompose, SpeakerUnit
from zunda_w.voice_vox import VoiceVoxProfile


class API:
    def __init__(self, cache_dir: str = '.cache', cache_tts: str = '.tts', profile=None, speaker_id=3):
        self.cache_dir = cache_dir
        self.cache_tts = cache_tts
        self.profile = profile
        self.speaker_id = speaker_id
        self.engine_dir = cache.user_cache_dir('voicevox')

    def text_to_speech(self, srt: Union[str, List[srt.Subtitle]], auto_close: bool = True,
                       voicevox_process: Optional[Popen] = None) -> Tuple[Sequence[str], Popen]:
        try:
            # launch process if not before launch.
            if voicevox_process is None:
                voicevox_process = voice_vox.launch_voicevox_engine(
                    download_voicevox.extract_engine(root_dir=self.engine_dir))
            if self.profile is None:
                profile = VoiceVoxProfile()
            tts_files = voice_vox.run(srt,
                                      speaker=self.speaker_id,
                                      root_dir=self.cache_dir,
                                      output_dir=self.cache_tts,
                                      query=profile)
        finally:
            if voicevox_process is not None and auto_close:
                voicevox_process.terminate()
                voicevox_process.poll()
        return tts_files, voicevox_process

    def chatgpt_to_speech(self, question: str, merge: bool = False, output: Optional[str] = None,
                          voicevox_process=None, auto_close=True, with_question: bool = False):
        from zunda_w.apis.chatgpt import run, response_as_srt
        # Send Request to ChatGPT
        name, response = run(question)
        subtitles = response_as_srt(response)
        # Answer Text to Speech
        tts_files, voicevox_process = self.text_to_speech(subtitles, auto_close=auto_close,
                                                          voicevox_process=voicevox_process)
        question_audio = None
        if with_question:
            question_audio, _ = self.text_to_speech([srt.Subtitle(1, timedelta.min, timedelta.min, question)],
                                                    auto_close=auto_close,
                                                    voicevox_process=voicevox_process)
        time_duration = subtitles[-1].end
        if merge:
            sound = edit.arrange(SpeakerCompose(
                [SpeakerUnit(s, AudioSegment.from_file(a)) for s, a in zip(subtitles, tts_files)],
                time_duration
            ))
            answer_audio = output if output else os.path.join(self.cache_dir, 'chatgpt', f'{question}.wav')
            Path(answer_audio).parent.mkdir(parents=True, exist_ok=True)
            sound.export(answer_audio)
            return question_audio, answer_audio, voicevox_process
        else:
            return question_audio, tts_files, voicevox_process

    def chatgpt_to_speech_from_file(self, file: str, merge: bool = True, root_dir: Optional[str] = None):
        questions = Path(file).read_text().splitlines()
        results = []
        process = None
        try:
            for q in questions:
                output_path = os.path.join(root_dir, f'A_{q}.wav') if root_dir else None
                q, a, process = self.chatgpt_to_speech(q, merge, output_path, process, auto_close=False,
                                                       with_question=True)
                results.append([q, a])
        except Exception as e:
            print(e)
        finally:
            if process:
                process.terminate()
                process.poll()
        return results


if __name__ == '__main__':
    fire.Fire((API()))
