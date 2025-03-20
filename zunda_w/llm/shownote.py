from pathlib import Path

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage


def create_show_note(transcript: str, resource_note: str) -> str:
    """
    ポッドキャストの文字起こしをもとにショーノートを作成する
    :param transcript: ポッドキャストの文字起こし
    :param resource_note: リソースノート
    :return: ショーノート
    """

    system_message = SystemMessage(
        "あなたはラジオディレクターです。ポッドキャストを文字起こしした文章を与えるので、トピックごとのショーノートを作成してください。\n ")
    llm = init_chat_model(model="gpt-4o", model_provider="openai", temperature=0, max_tokens=4000)
    history = [
        HumanMessage(transcript),
    ]

    response = llm.invoke([system_message] + history)
    history.append(HumanMessage(response.content))
    history.append(HumanMessage(
        f"ポッドキャスト収録時に参考にした資料です。\nショーノートにこれらの資料のリンクを合わせて再構成してください。{resource_note}#出力"))
    response2 = llm.invoke([system_message] + history)
    history.append(HumanMessage(response2.content))
    history.append(HumanMessage("この配信に視聴者が目を引くようなタイトルをつけてください"))
    response3 = llm.invoke([system_message] + history)

    Path("show_note1.json").write_text(response.text())
    Path("show_note2.json").write_text(response2.text())
    Path("show_note3.json").write_text(response3.text())

    # print(response.usage)
    # print(response2.usage)
    # print(response3.usage)

    return response2.content, response3.content
