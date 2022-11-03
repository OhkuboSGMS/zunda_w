# zunda-ASMR

zunda-ASMR is speech to text to speech by voicevox(+α) and whisper .

voicevox(+α) + whisper による speech to text to speech(STS)

> ずんだもんささやき声すこすこスコティッシュフォールド

# Install

```
pip install git+https://github.com/OhkuboSGMS/zunda-ASMR 
```
# Run
```zunda <audio_file> --output <output_file_name>```
# Author

Okubo Shigemasa

* Twitter  [Alt_Shift_N](https://twitter.com/Alt_Shift_N)
* Github   [OhkuboSGMS](https://github.com/OhkuboSGMS)

# License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

# TODO

```
キャッシュファイルによる再生成条件の決定
 生成パラメータが変わらなければ，生成済みのキャッシュファイルが使える
 キャッシュフォルダから名前を除く
 
1人でしゃべっていて，位置合わせを変えなければ，説明動画も作れるか?
ボイスボックスの説明動画をつくる？

字幕,画像，ポッドキャストの動画化

Text to Speechの汎用化
ひろゆき　:https://github.com/tsukumijima/TarakoTalk
声色フォント :https://coeiroink.com/download
などなど
```