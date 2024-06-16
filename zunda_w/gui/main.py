import asyncio
import os
from asyncio import sleep
from pathlib import Path
from typing import Final, List

import flet as ft
import markdown
import yaml
from flet_core import margin
from loguru import logger
from omegaconf import OmegaConf, SCMode
from pydub import effects

from zunda_w import file_hash
from zunda_w.apis import hackmd
from zunda_w.apis import share
from zunda_w.apis.podcast_upload import publish
from zunda_w.constants import list_preset
from zunda_w.llm import create_podcast_title
from zunda_w.srt_ops import sort_srt_files
from zunda_w.util import file_uri, read_srt
from zunda_w.words import WordFilter


def read_preset(preset_name: str, preset_dir: str):
    publish_conf_path = os.path.join(preset_dir, f"{preset_name}.yml")
    if not os.path.exists(publish_conf_path):
        logger.warning(f"Not Found Publish Preset: {publish_conf_path}")
        return None

    return yaml.load(open(publish_conf_path), Loader=yaml.SafeLoader)


def create_output_dir_if_not_exists(root_dir: str, name: str) -> str:
    output_path = os.path.join(root_dir, name)
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    return output_path


class AudioFile(ft.UserControl):
    """
    音声と字幕ファイルを選択するためのコンポーネント
    """
    extensions = ['wav', 'mp3', 'm4a', 'srt']

    def __init__(self, status_change, delete):
        super().__init__()
        self.path = None
        self.file_name = '<File Path>'
        self.file_picker = ft.FilePicker(on_result=self.open_file)
        self.status_change = status_change
        self.delete = delete

    def build(self):
        self.display_path = ft.Text(
            value=self.file_name,
            size=15,
            width=500
        )

        async def pick(_):
            return await self.file_picker.pick_files_async(
                allowed_extensions=self.extensions)

        self.display_view = ft.Container(
            margin=margin.only(left=20),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self.display_path,
                    ft.Row(
                        spacing=0,
                        controls=[
                            ft.IconButton(
                                icon=ft.icons.UPLOAD_OUTLINED,
                                tooltip="Open File",
                                on_click=pick
                            ),
                            ft.IconButton(
                                ft.icons.DELETE_OUTLINE,
                                tooltip="Delete To-Do",
                                on_click=self.delete_clicked,
                            ),
                        ],
                    ),
                ],
            )
        )
        return ft.Column(controls=[self.display_view, ])

    async def did_mount_async(self):
        self.page.overlay.append(self.file_picker)
        await self.page.update_async()

    async def will_unmount_async(self):
        self.page.overlay.remove(self.file_picker)
        await self.page.update_async()

    async def open_file(self, e: ft.FilePickerResultEvent):
        selected_file = (
            e.files[0].path if e.files else None
        )
        if selected_file:
            self.path = selected_file
            self.display_path.value = self.path
            await self.update_async()

    async def status_changed(self, e):
        await self.status_change(self)

    async def delete_clicked(self, e):
        await self.delete(self)


class ConverterApp(ft.UserControl):
    is_convert = False

    def __init__(self, default_preset=(), publish_presets=(), default_output_dir="./output"):
        super().__init__()
        self.PRESETS: Final[List[str]] = default_preset
        self.PUBLISH_PRESETS: Final[List[str]] = publish_presets
        self.OUTPUT_DIR: Final[str] = default_output_dir
        self.podcast_meta = {}

    def build(self):
        self.hack_md_memo_text = ft.Text("HackMD Memo:<Empty>")
        self.audio_files = ft.Column(
            controls=[
                AudioFile(self.task_status_change, self.delete_file_picker),
                AudioFile(self.task_status_change, self.delete_file_picker)
            ]
        )
        self.preset_select = ft.Dropdown(
            width=200,
            options=[ft.dropdown.Option(key=p, text=p) for p in self.PRESETS],
            value=self.PRESETS[0]
        )
        self.publish_select = ft.Dropdown(
            width=150,
            options=[ft.dropdown.Option(key=p, text=p) for p in self.PUBLISH_PRESETS],
            value=self.PUBLISH_PRESETS[0]
        )
        self.note_select = ft.Dropdown(
            width=150,
        )

        self.progress = ft.Row(
            visible=False,
            controls=[
                ft.Text("Audio to Text to Audio..."),
                ft.ProgressBar(width=400, color="amber", bgcolor="#eeeeee")
            ]
        )
        self.output_dir = ft.TextField(label="OutputDirectory")
        self.publish_button = ft.ElevatedButton('Publish', visible=True, on_click=self.publish_to_podcast)
        self.title_text = ft.Text("<title_text>")
        # application's root control (i.e. "view") containing all other controls
        return ft.Column(
            width=600,
            expand=False,
            controls=[
                ft.Row(
                    [ft.Text(value="とにかくヨシ！Studio", style=ft.TextThemeStyle.HEADLINE_MEDIUM)],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Row(
                    controls=[
                        ft.Text("Publish Preset:"),
                        self.publish_select
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Row(
                    controls=[
                        self.hack_md_memo_text,
                        self.note_select,
                        ft.ElevatedButton('List Memo',
                                          on_click=self.get_memos),
                        ft.ElevatedButton('Get Memo',
                                          on_click=self.get_memo_from_hackmd)
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Divider(),
                ft.Column(
                    spacing=25,
                    controls=[
                        self.audio_files,
                    ],
                ),
                ft.Row(
                    controls=[
                        ft.FloatingActionButton(
                            icon=ft.icons.ADD, on_click=self.add_file_picker
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END
                ),
                ft.Divider(),
                ft.Row(
                    controls=[
                        ft.Text("Preset:"),
                        self.preset_select
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Row(
                    controls=[
                        ft.Text("Output :"),
                        self.output_dir
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Divider(),
                ft.Row(
                    controls=[
                        ft.ElevatedButton('Convert',
                                          on_click=self.convert),
                        self.progress
                    ],
                    alignment=ft.MainAxisAlignment.START
                ),
                ft.Row(
                    controls=[
                        ft.ElevatedButton('Ready for Publish', visible=True, on_click=self.publish_setting),
                        self.title_text
                    ],
                    alignment=ft.MainAxisAlignment.START
                ),
                ft.Row(
                    controls=[
                        self.publish_button
                    ],
                    alignment=ft.MainAxisAlignment.START
                )
            ],
        )

    async def get_memos(self, e):
        """
        HackMDのメモを取得してドロップダウンにセットする
        Publish Presetのtagを取得して、そのtagでメモをフィルタリングして取得
        :param e:
        """
        from zunda_w.apis.hackmd import get_notes
        team_path = os.environ["HACKMD_TEAM_PATH"]
        publish_conf = read_preset(self.publish_select.value, os.environ["APP_PUBLISH_PRESET_DIR"])
        if publish_conf and publish_conf["note"]["tag"]:
            notes = get_notes(team_path, tag=publish_conf["note"]["tag"])
            self.note_select.options = [ft.dropdown.Option(key=n["id"], text=n["title"]) for n in notes]
            self.note_select.value = notes[0]["id"]
        else:
            logger.warning(f"No tag in publish preset:{self.publish_select.value}")
        await self.update_async()

    async def get_memo_from_hackmd(self, e):
        """
        選択されたメモを取得、フォルダを作成して、メモを保存
        :param e:
        :return:
        """
        publish_conf = read_preset(self.publish_select.value, os.environ["APP_PUBLISH_PRESET_DIR"])
        if not publish_conf or not publish_conf["note"]["tag"]:
            raise ValueError("No tag in publish preset")

        # TODO 最新のnoteを取得するのではなく、選択したnoteを取得するようにする。
        # TODO noteがフィルタではじかれた場合はエラーを出力する
        # 2022/01/01のようなタイトル,mdの中身
        dir_title, content = hackmd.get_note(os.environ["HACKMD_TEAM_PATH"], tag=publish_conf["note"]["tag"])

        # 生成したメタデータを保存、uiに反映
        output_dir_path: str = create_output_dir_if_not_exists(self.OUTPUT_DIR, dir_title)
        logger.debug(f"Create Output Dir: {os.path.abspath(output_dir_path)}")
        memo_path = f"{output_dir_path}/memo.md"
        Path(memo_path).write_text(content)

        self.podcast_meta = {
            "description": content,
            "memo_path": memo_path,
        }
        self.hack_md_memo_text.value = f"HackMD Memo:{dir_title}"
        self.output_dir.value = dir_title
        await self.update_async()

    async def publish_setting(self, e):
        """
        配信用に諸々を準備する
         1. 配信タイトルを生成
         2. 出力
         3.uiに反映
        :param e:
        :return:
        """
        from zunda_w.arg import Options
        if self.podcast_meta is None:
            raise ValueError("No Podcast Meta")
        if "memo_path" not in self.podcast_meta:
            raise ValueError("先にメモを取得してください")
        if "title" in self.podcast_meta:
            logger.debug("既に生成済みのタイトルがあるため、再生成しません")
            return
        if not self.output_dir.value:
            raise ValueError("Run Construct Title First!")

        memo_md: str = Path(self.podcast_meta["memo_path"]).read_text()
        conf = Options(target_dir=self.output_dir.value)
        publish_index = int(Path(os.environ["APP_PUBLISH_PRESET_DIR"]).joinpath("n.txt").read_text()) + 1
        title = f"{publish_index}.{create_podcast_title.summarize_title(memo_md)}"
        conf.tool_output("title.txt").write_text(title)

        logger.debug(f"title path:{conf.tool_output('title.txt')} ,title:{title}")
        self.podcast_meta["title"] = title
        self.podcast_meta["title_path"] = conf.tool_output("title.txt")

        # update ui
        self.title_text.value = title
        await self.update_async()

    async def publish_to_podcast(self, e):
        if self.output_file is None:
            print("Not Found Publish File")
            return
        try:
            share_url = await publish(
                os.environ["PODCAST_URL"],
                os.environ["PODCAST_EMAIL"],
                os.environ["PODCAST_PASSWORD"],
                os.path.abspath(self.output_file),
                Path(self.podcast_meta["title_path"]).read_text(),
                markdown.markdown(text=Path(self.podcast_meta["memo_path"]).read_text(), extensions=["mdx_linkify"]),
                # TODO publish.ymlから取得,
                timeout=360 * 1000  # 出すまでに時間がかかるので、長めに取っておく
                # thumbnail=os.environ["PODCAST_THUMBNAIL"] if "PODCAST_THUMBNAIL" in os.environ else None,
            )
            self.podcast_meta["share_url"] = share_url
            # OGタグが生成されるまで待つ
            await sleep(5)
            await share(share_url, None)
        except Exception as e:
            logger.exception(e)
            print(e)
        await self.update_async()

    async def update_progress(self, status: bool):
        self.is_convert = status
        self.progress.visible = status
        await self.update_async()

    async def task_convert(self, files, preset: str, publish_preset: str):
        """ポッドキャストの音声を変換(タスク)"""
        from zunda_w import __main__
        from zunda_w.arg import Options
        from zunda_w.edit import edit_from_yml
        files = list(filter(lambda x: x is not None, files))
        conf = OmegaConf.structured(Options(audio_files=files, preset=preset))

        publish_conf = read_preset(publish_preset, os.environ["APP_PUBLISH_PRESET_DIR"])
        if publish_conf is None:
            await self.update_progress(False)
            return
        if self.output_dir.value:
            conf.target_dir = self.output_dir.value

        if publish_conf.get("mode", "s2t2s") == "s2t2s":
            self.output_file = __main__._convert(conf)
        elif publish_conf.get("mode") == "editor":
            # TODO 修正
            # TODO anthropicのAPI
            # TODO 文字おこしの時系列順でショーノートを作る

            conf.preset = preset
            conf = OmegaConf.to_container(conf, structured_config_mode=SCMode.INSTANTIATE)
            _audio = edit_from_yml(files, publish_conf)
            _audio = effects.normalize(_audio)
            output_audio = conf.tool_output("mix.wav")
            _audio.export(output_audio, format="wav")
            conf.audio_files = [output_audio]
            print(output_audio)
            from zunda_w.whisper_json import (
                transcribe_with_config,
                whisper_context,
            )
            from zunda_w.llm import shownote
            with whisper_context():
                audio_hash = file_hash(output_audio)
                stt_file = list(
                    transcribe_with_config(
                        conf.audio_files,
                        conf.whisper_profile,
                        root_dir=os.path.join(conf.data_dir, audio_hash),
                        meta_data="",
                    ))
                print(stt_file)
                compose = sort_srt_files(stt_file, word_filter=WordFilter(conf.word_filter))
                output_srt = conf.tool_output("stt.srt")
                compose.to_srt(output_srt)
                if "description" in self.podcast_meta:
                    output_show_note = conf.tool_output("show_note.md")
                    if not os.path.exists(output_show_note):
                        print("Create Show Note")

                        transcript = "\n".join(map(lambda x: x.content, read_srt(output_srt)))
                        show_note, title = shownote.create_show_note(transcript, self.podcast_meta["description"])
                        Path(output_show_note).write_text(show_note)
                    else:
                        print(f"Show Note Exists: {output_show_note}")
                print(file_uri(str(conf.tool_output)))
            self.output_file = output_audio

        self.progress.visible = False
        self.is_convert = False
        self.publish_button.visible = True
        await self.update_async()

    async def convert(self, e):
        """ポッドキャストの音声を変換"""
        files = list(map(lambda x: x.path, self.audio_files.controls))
        preset = self.preset_select.value
        publish_preset = self.publish_select.value
        print(files, preset, publish_preset)
        self.is_convert = True
        self.progress.visible = True
        await self.update_async()
        asyncio.create_task(self.task_convert(files, preset, publish_preset))

    async def add_file_picker(self, e):
        """
        FilePickerのItemを追加する
        :param e:
        :return:
        """
        audio_file_picker = AudioFile(self.task_status_change, self.delete_file_picker)
        self.audio_files.controls.append(audio_file_picker)
        await self.update_async()

    async def task_status_change(self, task):
        await self.update_async()

    async def delete_file_picker(self, task):
        """
        FilePickerのItemを削除する
        :param task:
        :return:
        """
        self.audio_files.controls.remove(task)
        await self.update_async()

    async def tabs_changed(self, e):
        await self.update_async()

    async def update_async(self):
        await super().update_async()


async def main(page: ft.Page):
    presets = list_preset(os.environ["APP_EDIT_PRESET_DIR"], patterns=["*.yaml"])
    publish_preset = list_preset(os.environ["APP_PUBLISH_PRESET_DIR"], patterns=["*.yml"])
    page.title = "とにかくヨシ！Studio"
    page.show_semantics_debugger = False
    page.window_visible = True

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE

    # create app control and add it to the page
    await page.add_async(ConverterApp(default_preset=presets, publish_presets=publish_preset))


def __main__():
    ft.app(main, view=ft.AppView.FLET_APP_HIDDEN)
