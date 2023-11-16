import os.path

import fire
import requests

ROOT_URL = "http://localhost:50032"

"""
TODO エンジンが無い場合はコマンド上でない旨を書いて，手動でダウンロードしてもらう
TODO /v1/download_infosでダウンロード可能なキャラ一覧をとる
TODO 合成音声作成時に指定したキャラが無ければ，動的にダウンロード
TODO /v1/synthesisで合成  
request_body  
{
  "speakerUuid": "3c37646f-3881-5374-2a83-149267990abc",
  "styleId": 0,
  "text": "こんにちわ！",
  "speedScale": 1.0,
  "volumeScale": 1.0,
  "pitchScale": 0.0,
  "intonationScale": 1.0,
  "prePhonemeLength": 0.0,
  "postPhonemeLength": 0.0,
  "outputSamplingRate": 44100
}
"""


def get_speaker_info():
    url = f"{ROOT_URL}/v1/speakers"
    print(url)
    result = requests.get(url)
    if result.status_code == 200:
        speakers = result.json()

        return speakers
    raise requests.HTTPError(result)


if __name__ == "__main__":
    fire.Fire({"speaker": get_speaker_info})
