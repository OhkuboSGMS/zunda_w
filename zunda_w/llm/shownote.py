from functools import partial
from pathlib import Path

import anthropic
from anthropic.types import Message


def create_show_note(transcript: str, resource_note: str) -> str:
    """
    ポッドキャストの文字起こしをもとにショーノートを作成する
    :param transcript: ポッドキャストの文字起こし
    :param resource_note: リソースノート
    :return: ショーノート
    """
    system_message = "あなたはラジオディレクターです。ポッドキャストを文字起こしした文章を与えるので、トピックごとのショーノートを作成してください。チャットとしての返答はせずに出力だけ行ってください。"
    client = anthropic.Anthropic()  # defaults to os.environ.get("ANTHROPIC_API_KEY")
    # claude-3-sonnet-20240229
    # claude-3-opus-20240229
    request = partial(client.messages.create,
                      model="claude-3-5-sonnet-20240620",
                      # claude-3-sonnet-20240229",
                      max_tokens=4000,
                      temperature=0,
                      system=system_message,
                      )
    history = [
        {"role": "user", "content": transcript},
    ]

    response = request(messages=history)
    # TODO: hisotryを分ける
    history.append({"role": response.role, "content": response.content})
    history.append(
        {"role": "user", "content": f"ポッドキャスト収録時に参考にした資料です。\nショーノートにこれらの資料のリンクを合わせて再構成してください。{resource_note}#出力"})
    response2 = request(messages=history)
    history.append({"role": response2.role, "content": response2.content})
    history.append({"role": "user", "content": "この配信に視聴者が目を引くようなタイトルをつけてください"})
    response3: Message = request(messages=history)
    Path("show_note1.json").write_text(response.to_json())
    Path("show_note2.json").write_text(response2.to_json())
    # Path("show_note3.json").write_text(response3.to_json())

    print(response.usage)
    # print(response2.usage)
    # print(response3.usage)

    return response2.content[0].text, response3.content[0].text
