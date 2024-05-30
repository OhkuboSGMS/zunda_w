import asyncio
import os
from asyncio import sleep
from pathlib import Path

import flet as ft
import yaml
from flet_core import margin
from loguru import logger
from omegaconf import OmegaConf, SCMode
from pydub import effects

from zunda_w import file_hash
from zunda_w.apis import share
from zunda_w.srt_ops import sort_srt_files
from zunda_w.util import file_uri, read_srt
from zunda_w.words import WordFilter


def read_preset(preset_name: str, preset_dir: str):
    publish_conf_path = os.path.join(preset_dir, f"{preset_name}.yml")
    if not os.path.exists(publish_conf_path):
        logger.warning(f"Not Found Publish Preset: {publish_conf_path}")
        return None

    return yaml.load(open(publish_conf_path), Loader=yaml.SafeLoader)


class AudioFile(ft.UserControl):
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
                allowed_extensions=['wav', 'mp3', 'srt'])

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
    output_file = None
    podcast_meta = {}
    url = None

    def build(self):
        # TODO 修正
        PUBLISH_PRESET = list(map(lambda x: str(x.stem), Path(os.environ["APP_PUBLISH_PRESET_DIR"]).glob("*.yml")))
        from zunda_w.constants import update_preset
        update_preset("./preset_config")
        from zunda_w.constants import PRESET_NAME

        self.hack_md_memo_text = ft.Text("HackMD Memo:<Empty>")
        self.audio_files = ft.Column(
            controls=[
                AudioFile(self.task_status_change, self.delete),
                AudioFile(self.task_status_change, self.delete)
            ]
        )
        self.preset_select = ft.Dropdown(
            width=200,
            options=[ft.dropdown.Option(key=p, text=p) for p in PRESET_NAME],
            value=PRESET_NAME[0]
        )
        self.publish_select = ft.Dropdown(
            width=150,
            options=[ft.dropdown.Option(key=p, text=p) for p in PUBLISH_PRESET],
            value=PUBLISH_PRESET[0]
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
                        ft.ElevatedButton('Get Memo',
                                          on_click=self.get_memos),
                        ft.ElevatedButton('Construct Title',
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
                            icon=ft.icons.ADD, on_click=self.add
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
                        ft.ElevatedButton('Construct', visible=True, on_click=self.publish_setting),
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
        HackMDのメモを取得して表示する
        """
        from zunda_w.apis.hackmd import get_notes
        team_path = os.environ["HACKMD_TEAM_PATH"]
        publish_conf = read_preset(self.publish_select.value, os.environ["APP_PUBLISH_PRESET_DIR"])
        if publish_conf and publish_conf["note"]["tag"]:
            notes = get_notes(team_path, tag=publish_conf["note"]["tag"])
            self.note_select.options = [ft.dropdown.Option(key=n["id"], text=n["title"]) for n in notes]
            self.note_select.value = notes[0]["id"]
        await self.update_async()

    async def get_memo_from_hackmd(self, e):
        """
        Construct Titleをクリックしたときにの動作
        選択されたHackMdのメモを取得して
        :param e:
        :return:
        """
        from zunda_w.apis.hackmd import get_note
        team_path = os.environ["HACKMD_TEAM_PATH"]
        publish_conf = read_preset(self.publish_select.value, os.environ["APP_PUBLISH_PRESET_DIR"])
        if not publish_conf or not publish_conf["note"]["tag"]:
            raise ValueError("No tag in publish preset")

        title, content = get_note(team_path, tag=publish_conf["note"]["tag"])
        podcast_title = title
        # TODO fix output style
        output_dir = f"./output/{title}"
        os.makedirs(output_dir, exist_ok=True)
        # title_path = f"{output_dir}/title.txt"
        # with open(title_path, "w") as f:
        #     f.write(podcast_title)
        memo_path = f"{output_dir}/memo.md"
        with open(memo_path, "w") as f:
            f.write(content)

        self.podcast_meta = {
            # "title": podcast_title,
            "description": content,
            # "title_path": title_path,
            "memo_path": memo_path,
        }
        self.hack_md_memo_text.value = f"HackMD Memo:{title}"
        self.output_dir.value = title
        await self.update_async()

    async def publish_setting(self, e):
        from zunda_w.arg import Options
        from zunda_w.apis import hackmd
        if self.podcast_meta is None:
            raise ValueError("No Podcast Meta")
        if "memo_path" not in self.podcast_meta:
            raise ValueError("Run Construct Title First!")
        if "title" in self.podcast_meta:
            return
        if not self.output_dir.value:
            raise ValueError("Run Construct Title First!")
        memo_md = Path(self.podcast_meta["memo_path"]).read_text()
        conf = Options()
        conf.target_dir = self.output_dir.value
        publish_index = int(Path(os.environ["APP_PUBLISH_PRESET_DIR"]).joinpath("n.txt").read_text()) + 1
        with open(conf.tool_output("title.txt"), "w") as f:
            title = hackmd.summarize_title(memo_md)
            title = f"{publish_index}.{title}"
            f.write(title)
        print(conf.tool_output('title.txt'))
        self.podcast_meta["title"] = title
        self.podcast_meta["title_path"] = conf.tool_output("title.txt")

        self.title_text.value = title
        await self.update_async()

    async def publish_to_podcast(self, e):
        from zunda_w.apis.podcast_upload import publish
        if self.output_file is None:
            print("Not Found Publish File")
            return
        try:
            # TODO shownoteのmarkdownをhtmlに変換
            #     markdown.markdownFromFile(input=md, output=md.replace(".md", ".html"),
            #                               extensions=["mdx_linkify"])
            share_url = await publish(
                os.environ["PODCAST_URL"],
                os.environ["PODCAST_EMAIL"],
                os.environ["PODCAST_PASSWORD"],
                os.path.abspath(self.output_file),
                Path(self.podcast_meta["title_path"]).read_text(),
                Path(self.podcast_meta["memo_path"]).read_text(),
                # TODO publish.ymlから取得,
                timeout=360 * 1000  # 出すまでに時間がかかるので、長めに取っておく
                # thumbnail=os.environ["PODCAST_THUMBNAIL"] if "PODCAST_THUMBNAIL" in os.environ else None,
            )
            self.url = share_url
            # OGタグが生成されるまで待つ
            await sleep(5)
            await share(self.url, None)
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

    async def add(self, e):
        audio_file_picker = AudioFile(self.task_status_change, self.delete)
        self.audio_files.controls.append(audio_file_picker)
        await self.update_async()

    async def task_status_change(self, task):
        await self.update_async()

    async def delete(self, task):
        self.audio_files.controls.remove(task)
        await self.update_async()

    async def tabs_changed(self, e):
        await self.update_async()

    async def update_async(self):
        await super().update_async()


async def main(page: ft.Page):
    page.title = "とにかくヨシ！Studio"
    page.show_semantics_debugger = False
    page.window_visible = True

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE

    # create app control and add it to the page
    await page.add_async(ConverterApp())


def __main__():
    ft.app(main, view=ft.AppView.FLET_APP_HIDDEN)
