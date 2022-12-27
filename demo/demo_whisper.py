from zunda_w.whisper_json import transcribe_non_silence, WhisperProfile


def main():
    waves = ['.cache/8146b376e04b54cba5ea26b0903f8a7f/.silence/0001.wav']
    meta = ['.cache/8146b376e04b54cba5ea26b0903f8a7f/.silence/0001.meta']

    result = transcribe_non_silence(waves, meta,WhisperProfile())
    print(list(result))


if __name__ == '__main__':
    main()
