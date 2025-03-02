import re
from typing import List

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage


def create(srt_text: str) -> List[str]:
    # 正規表現パターン
    pattern = r'\w+'
    llm = init_chat_model(model="gpt-4o",model_provider="openai",
                          temperature=0.1, max_tokens=256, top_p=1, frequency_penalty=0, presence_penalty=0)
    messages = [
        SystemMessage("ポッドキャストの文字起こしをしたテキストを与えます。\n文字起こしをブログ記事として投稿する際のカテゴリを最大5個まで考えてください。必ず5個作成する必要はありません。\n\n\n#出力例\n[ポッドキャスト,アーカイブ,カメラ]"),
        HumanMessage(f"## 入力\n{srt_text}\n\n##出力")
    ]
    response = llm.invoke(messages)
    category_text = response.text()
    # 単語ごとに分割
    categories = re.findall(pattern, category_text)
    return categories


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    srt_text = """どうもどうも、こんにちは。今日は、ポッドキャストの文字起こしをもとに、ブログ記事を作成するためのカテゴリを考えていきます。ポッドキャストの文字起こしをしたテキストを与えます。文字起こしをブログ記事として投稿する際のカテゴリを最大10個まで考えてください。必ず10個作成する必要はありません。"""
    print(create(srt_text))
