import openai


def summarize_title(content: str):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are help full assistant.\nマークダウン形式のテキストを与えます与えられたテキストからh1を抽出して/で区切って出力してください\n\n例:\n入力:\n# ポッドキャストを自動作成\nhttps://note.com/shingo2000/n/n31ebc6dfc28f\n# ネットで申し込みは誰のノルマか？\n保険に申し込んだ\n県民共済-総合型2\n\n### チップの話\nhttps://www.jiji.com/jc/v8?id=20230606world\nhttps://b.hatena.ne.jp/entry/s/news.yahoo.co.jp/articles/a61f20bb9b9bb577ca519655c7c250eb16af3236\n\n出力:\nポッドキャストを自動生成/ネットに申し込みは誰のノルマか？"
            },
            {
                "role": "user",
                "content": content
            },
        ],
        temperature=0.1,
        max_tokens=256,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response["choices"][0]["message"]["content"]
