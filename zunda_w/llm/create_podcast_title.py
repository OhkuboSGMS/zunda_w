from langchain.chat_models import init_chat_model


def summarize_title(content: str):
    llm = init_chat_model(model="gpt-4o", model_provider="openai", temperature=0.5, max_tokens=512, top_p=1,
                          frequency_penalty=0, presence_penalty=0)
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant.\nマークダウン形式のテキストを与えます.与えられたテキストからh1を抽出して/で区切って出力してください\n\n例:\n入力:\n# ポッドキャストを自動作成\nhttps://note.com/shingo2000/n/n31ebc6dfc28f\n# ネットで申し込みは誰のノルマか？\n保険に申し込んだ\n県民共済-総合型2\n\n### チップの話\nhttps://www.jiji.com/jc/v8?id=20230606world\nhttps://b.hatena.ne.jp/entry/s/news.yahoo.co.jp/articles/a61f20bb9b9bb577ca519655c7c250eb16af3236\n\n出力:\nポッドキャストを自動生成/ネットに申し込みは誰のノルマか？"
        },
        {
            "role": "user",
            "content": content
        },
    ]

    response = llm.invoke(messages)
    return response.text()
