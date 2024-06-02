import os
import re
from typing import Optional

import requests

TITLE_PATTERN = r'(\d{4})/(\d{2})/(\d{2})'
BASE_URL = "https://api.hackmd.io/v1"


def filter_by_title(content: str):
    """
    ノートのタイトルをフィルタリングする.
    パターンに合致する場合はTrueを返す.
    タイトル例：
    ok: 2022/01/01
    ng: 2022/1/1

    :param content:
    :return:
    """
    return re.match(TITLE_PATTERN, content) is not None


def get_notes(team_path: str, tag: Optional[str] = None):
    """Get the latest notes from the team.(HackMD API)
    Get a list of notes from the team: https://hackmd.io/@hackmd-api/developer-portal/https%3A%2F%2Fhackmd.io%2F%40hackmd-api%2Fuser-notes-api
    :param team_path: The team path of the note.
    :param tag: The tag of the note.
    """
    if os.environ["HACKMD_TOKEN"] is None:
        raise ValueError("Please set environment variable, HACKMD_TOKEN")
    headers = {
        "Authorization": f"Bearer {os.environ['HACKMD_TOKEN']}"
    }
    list_team_notes = f"/teams/{team_path}/notes"
    res = requests.get(BASE_URL + list_team_notes, headers=headers)
    notes = res.json()
    if tag:
        notes = list(filter(lambda x: tag in x["tags"], notes))
    return notes


def get_note(team_path: str, tag: Optional[str] = None):
    """Get the latest note from the team.(HackMD API)

    filter_by_title: ノートのタイトル特定のパターンに限定する.
    :param team_path: The team path of the note.
    """
    notes = get_notes(team_path, tag)
    latest_note = list(filter(lambda x: filter_by_title(x["title"]), notes))
    latest_note = latest_note[0]
    note_id = latest_note["id"]

    get_note_api = f"/notes/{note_id}"
    headers = {
        "Authorization": f"Bearer {os.environ['HACKMD_TOKEN']}"
    }
    note = requests.get(BASE_URL + get_note_api, headers=headers).json()
    return note["title"], note["content"]
