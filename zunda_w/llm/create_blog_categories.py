import os
import re
from typing import List

import openai

MODEL_NAME = "gpt-4o"


def create(srt_text: str) -> List[str]:
    # 正規表現パターン
    pattern = r'\w+'
    openai.api_key = os.getenv("OPENAI_API_KEY")
    response = openai.ChatCompletion.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "text": "ポッドキャストの文字起こしをしたテキストを与えます。\n文字起こしをブログ記事として投稿する際のカテゴリを最大5個まで考えてください。必ず5個作成する必要はありません。\n\n\n#出力例\n[ポッドキャスト,アーカイブ,カメラ]",
                        "type": "text"
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"## 入力\n{srt_text}\n\n##出力"
                    }
                ]
            }
        ],
        temperature=0.1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    category_text = response.choices[0].message.content
    # 単語ごとに分割
    categories = re.findall(pattern, category_text)
    return categories


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    srt_text = """どうもどうも、こんにちは。今日は、ポッドキャストの文字起こしをもとに、ブログ記事を作成するためのカテゴリを考えていきます。ポッドキャストの文字起こしをしたテキストを与えます。文字起こしをブログ記事として投稿する際のカテゴリを最大10個まで考えてください。必ず10個作成する必要はありません。"""
    print(create(srt_text))
