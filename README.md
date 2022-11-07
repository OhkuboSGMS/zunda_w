# zunda-ASMR

zunda-ASMR is speech to text to speech by voicevox(+α) and whisper .

voicevox(+α) + whisper による speech to text to speech(STS)

> ずんだもんささやき声すこすこスコティッシュフォールド

![zunda-ASMR](https://user-images.githubusercontent.com/11247895/199970004-a262a1b3-8e0a-4324-8d5b-0da1525186c4.png)



https://user-images.githubusercontent.com/11247895/200321495-f8ce3665-afa1-4641-8202-73830df6aecc.mp4


# Install
⚠️現在python=3.8限定⚠️
```
pip install git+https://github.com/OhkuboSGMS/zunda-ASMR 
```
# Run
```
zunda <audio_file> --output <output_file_name>
```
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
