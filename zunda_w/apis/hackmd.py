import os
import re

import openai
import requests


def summarize_title(content: str):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
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


def filter_by_title(content: str):
    pattern = r'(\d{4})-(\d{2})-(\d{2})'
    return re.match(pattern, content) is not None


def get_latest_note(team_path: str):
    """Get the latest note from the team.(HackMD API)
    :param team_path: The team path of the note.
    """
    headers = {
        "Authorization": f"Bearer {os.environ['HACKMD_TOKEN']}"
    }
    base_url = "https://api.hackmd.io/v1"
    list_team_notes = f"/teams/{team_path}/notes"
    res = requests.get(base_url + list_team_notes, headers=headers)
    latest_note = list(filter(lambda x: filter_by_title(x["title"]), res.json()))
    latest_note = latest_note[0]
    latest_note_id = latest_note["id"]
    get_note = f"/notes/{latest_note_id}"
    note = requests.get(base_url + get_note, headers=headers).json()
    return note["title"], note["content"]


def create_podcast_description(team_path: str):
    """Create a podcast description from the latest note of the team.
    :param team_path: The team path of the note.
    :param output_dir: The output directory of the podcast description.
    """
    title, content = get_latest_note(team_path)
    podcast_title = summarize_title(content)
    return title, podcast_title, content
