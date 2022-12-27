from moviepy.audio.AudioClip import AudioClip
import numpy as np

clip = AudioClip(lambda t: 0, duration=5)
clip.write_audiofile('test.mp3',fps=44100)
