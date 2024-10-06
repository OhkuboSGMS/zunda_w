from typing import List, Optional

import fire
from more_itertools import chunked
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, LukeConfig
from transformers import pipeline

from zunda_w.postprocess.srt import tag
from zunda_w.util import read_srt, write_srt


def get_sentiment(text: str):
    """
    https://huggingface.co/lxyuan/distilbert-base-multilingual-cased-sentiments-student

    テキストをポジティブ，ニュートラル，ネガティブの3段階に分類する.
    :param text:
    :return:
    """
    distilled_student_sentiment_classifier = pipeline(
        model="lxyuan/distilbert-base-multilingual-cased-sentiments-student",
        return_all_scores=True
    )
    # japanese
    print(distilled_student_sentiment_classifier("私はこの映画が大好きで、何度も見ます！"))


EMOTION_INDEX = {
    0: 'e:joy',  # うれしい
    1: 'e:sad',  # 悲しい
    2: 'e:anticipate',  # 期待
    3: 'e:surprise',  # 驚き
    4: 'e:anger',  # 怒り
    5: 'e:fear',  # 恐れ
    6: 'e:disgust',  # 嫌悪
    7: 'e:trust'  # 信頼
}
EMO_TAG = "e:"


def emotion() -> List[str]:
    return [v.replace("e:", "") for _, v in EMOTION_INDEX.items()]


def _get_emotion(text: List[str], batch: int = 8):
    """
    WRIME[https://github.com/ids-cv/wrime]
    https://huggingface.co/Mizuiro-sakura/luke-japanese-large-sentiment-analysis-wrime
    喜び、悲しみ、期待、驚き、怒り、恐れ、嫌悪、信頼 を分類
    """

    tokenizer = AutoTokenizer.from_pretrained("Mizuiro-sakura/luke-japanese-large-sentiment-analysis-wrime")
    config = LukeConfig.from_pretrained('Mizuiro-sakura/luke-japanese-large-sentiment-analysis-wrime',
                                        output_hidden_states=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        'Mizuiro-sakura/luke-japanese-large-sentiment-analysis-wrime', config=config)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        model.to("cuda")

    max_seq_length = 512
    result = []

    with torch.no_grad():
        for t in chunked(text, batch):
            token = tokenizer(t,
                              truncation=True,
                              max_length=max_seq_length,
                              padding="max_length",
                              return_tensors="pt").to(device)
            output = model(**token)
            max_index = torch.argmax(output.logits.cpu().detach(), dim=1)
            max_index = max_index.numpy().tolist()
            emos = [EMOTION_INDEX[index] for index in max_index]
            result.extend(emos)
    return result


def add_emotion_tag(srt_file: str, dst_file: Optional[str] = None) -> str:
    srts = read_srt(srt_file)
    text = [s.content for s in srts]
    emotions = _get_emotion(text)
    for srt, emo in zip(srts, emotions):
        srt.content = tag.as_tag(emo) + srt.content
    if dst_file:
        write_srt(dst_file, srts)
    else:
        write_srt(srt_file, srts)
    return srt_file


if __name__ == '__main__':
    fire.Fire(add_emotion_tag)
