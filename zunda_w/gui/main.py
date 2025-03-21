import asyncio
import os
from pathlib import Path
from typing import Final, List, Dict, Optional

import flet as ft
import markdown
import sfp_uploader
from flet_core import margin
from loguru import logger
from omegaconf import OmegaConf, SCMode

import rs_downloader
from zunda_w import file_hash
from zunda_w.apis import hackmd, share
from zunda_w.arg import Options
from zunda_w.constants import list_preset
from zunda_w.edit import edit_from_yml
from zunda_w.etc.fille import increment_file
from zunda_w.etc.timer import Timer
from zunda_w.llm import create_podcast_title, shownote, create_blog_categories
from zunda_w.postprocess import normalize
from zunda_w.srt_ops import sort_srt_files, srt_as_interview_blog_content
from zunda_w.util import file_uri, read_srt, read_preset
from zunda_w.words import WordFilter


async def show_snackbar(msg, e):
    snackbar = ft.SnackBar(ft.Text(msg))
    e.control.page.overlay.append(snackbar)
    snackbar.open = True
    await e.control.page.update_async()


def create_output_dir_if_not_exists(root_dir: str, name: str) -> str:
    output_path = os.path.join(root_dir, name)
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    return output_path


def convert(files, preset: str, publish_preset: str, output_dir: str, root_dir: Optional[str] = None):
    """
    ポッドキャストの音声を変換(タスク)
    :param files:
    :param preset:
    :param publish_preset:
    :param output_dir: 出力フォルダ名
    :param root_dir:  出力先のディレクトリ
    :return:
    """
    from zunda_w import __main__
    files = list(filter(lambda x: x is not None, files))
    conf = OmegaConf.structured(Options(audio_files=files, preset=preset))

    publish_conf = read_preset(publish_preset, os.environ["APP_PUBLISH_PRESET_DIR"])

    if publish_conf is None:
        # await self.update_progress(False)
        return None, "Publish Preset Not Found"
    if output_dir:
        conf.target_dir = output_dir

    if root_dir:
        conf.output_dir = root_dir

    if publish_conf.get("mode", "s2t2s") == "s2t2s":
        output_file = __main__._convert(conf)
        return output_file, None
    elif publish_conf.get("mode") == "editor":
        # TODO 修正
        # TODO anthropicのAPI
        # TODO 文字おこしの時系列順でショーノートを作る
        conf.preset = preset
        conf = OmegaConf.to_container(conf, structured_config_mode=SCMode.INSTANTIATE)
        _audio = edit_from_yml(files, publish_conf)
        output_audio = conf.tool_output("mix.wav")
        _audio.export(output_audio, format="wav")
        normalize.ffmpeg_normalize(output_audio, output_audio)
        conf.audio_files = [output_audio]
        print(output_audio)
        from zunda_w.transcribe import (
            transcribe_with_config,
            whisper_context,
        )
        with whisper_context(), Timer() as t:
            stt_files = []
            for idx, (original_audio, speaker_id) in enumerate(zip(files, conf.speakers)):
                audio_hash = file_hash(output_audio)
                stt_file = list(
                    transcribe_with_config(
                        [original_audio],
                        conf.whisper_profile,
                        root_dir=os.path.join(conf.data_dir, audio_hash),
                        meta_data=str(speaker_id),
                    ))
                print(stt_file)
                stt_files.extend(stt_file)

            compose = sort_srt_files(stt_files, word_filter=WordFilter(conf.word_filter))
            compose.to_srt(conf.tool_output("stt.srt"))
            print(file_uri(str(conf.tool_output)))
        logger.info(f"Transcribe Time:{t.elapsed:.2f}s")
        output_file = output_audio
        return output_file, None


def publish():
    pass  # TODO 共有の処理


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
        self.OUTPUT_ROOT_DIR: Final[str] = os.getenv("APP_OUTPUT_ROOT_DIR", default_output_dir)
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
                    [ft.Text(value=os.environ.get("APP_TITLE", "Podcast Studio"),
                             style=ft.TextThemeStyle.HEADLINE_MEDIUM)],
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
                        ft.Text(value="Create Memo with Preset"),
                        ft.ElevatedButton('Create',
                                          on_click=self.create_memo),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Row(
                    controls=[
                        self.hack_md_memo_text,
                        self.note_select,
                        ft.ElevatedButton('List Memo',
                                          on_click=self.list_memo),
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
                        ft.ElevatedButton('Download RS',
                                          on_click=self.download_from_rs),
                        ft.FloatingActionButton(
                            icon=ft.icons.ADD, on_click=self.add_file_picker
                        )
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
                        ft.ElevatedButton('Set File as Output',
                                          on_click=self.set_file_as_output),
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

    async def create_memo(self, e):
        """
        収録用のメモをpublish_settingから作成
        :param e:
        :return:
        """
        from zunda_w.apis.hackmd import create_memo
        team_path = os.environ["HACKMD_TEAM_PATH"]
        publish_conf = read_preset(self.publish_select.value, os.environ["APP_PUBLISH_PRESET_DIR"])

        create_memo(team_path,
                    tag=publish_conf["note"]["tag"],
                    template=publish_conf["note"]["template"],
                    title=None)
        await self.update_async()

    async def list_memo(self, e):
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
        memo_id = self.note_select.value
        if not memo_id:
            logger.warning("No Memo Selected")
            await show_snackbar("No Memo Selected", e)
            return
        publish_conf = read_preset(self.publish_select.value, os.environ["APP_PUBLISH_PRESET_DIR"])
        if not publish_conf or not publish_conf["note"]["tag"]:
            raise ValueError("No tag in publish preset")

        dir_title, content = hackmd.get_note(os.environ["HACKMD_TEAM_PATH"], memo_id)
        # Publish Config と合わせて出力フォルダを作成
        dir_title = f'{dir_title}_{publish_conf["note"]["type"]}'
        # 生成したメタデータを保存、uiに反映
        output_dir_path: str = create_output_dir_if_not_exists(self.OUTPUT_ROOT_DIR, dir_title)
        logger.debug(f"Create Output Dir: {Path(output_dir_path).absolute().as_uri()}")
        memo_path = f"{output_dir_path}/memo.md"
        Path(memo_path).write_text(content)

        self.podcast_meta = {
            "description": content,
            "memo_path": memo_path,
        }
        self.hack_md_memo_text.value = f"HackMD Memo:{dir_title}"
        self.output_dir.value = dir_title
        await self.update_async()

    async def download_from_rs(self, e):
        try:
            url = os.environ.get("APP_RS_URL", None)
            download_dir = os.environ.get("APP_RS_DOWNLOAD_DIR", None)
            memo_path = os.environ.get("APP_RS_DOWNLOAD_MEMO", None)
            if not download_dir or not memo_path or not url:
                raise ValueError(
                    "Download Dir or Memo Path is not set. Please set APP_RS_URL, APP_RS_DOWNLOAD_DIR, APP_RS_DOWNLOAD_MEMO")

            await rs_downloader.download(url, download_dir, memo_path)
        except Exception as e:
            logger.exception(e)

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
        publish_conf = read_preset(self.publish_select.value, os.environ["APP_PUBLISH_PRESET_DIR"])
        if not publish_conf or not publish_conf["note"]["tag"]:
            raise ValueError("No tag in publish preset")
        if self.podcast_meta is None:
            raise ValueError("No Podcast Meta")
        if "memo_path" not in self.podcast_meta:
            raise ValueError("先にメモを取得してください")
        if not self.output_dir.value:
            raise ValueError("Run Construct Title First!")

        memo_md: str = Path(self.podcast_meta["memo_path"]).read_text()
        conf = Options(target_dir=self.output_dir.value, output_dir=self.OUTPUT_ROOT_DIR)
        n_txt_file = Path(os.environ["APP_PUBLISH_PRESET_DIR"]).joinpath("n.txt")
        publish_index = int(n_txt_file.read_text()) + 1
        if not os.path.exists(conf.tool_output("title.txt")):
            title = f"{publish_index}{publish_conf['note']['type']}.{create_podcast_title.summarize_title(memo_md)}"
            logger.debug(f"タイトル生成: {title}")
            conf.tool_output("title.txt").write_text(title)
        else:
            title = conf.tool_output("title.txt").read_text()
            logger.debug(f"タイトル読み込み: {title}")
        # Show Noteの作成
        if "create_show_note" in publish_conf and publish_conf["create_show_note"]:
            output_show_note = conf.tool_output("show_note.md")
            output_transcript = conf.tool_output("stt.srt")
            if "description" in self.podcast_meta:
                if not os.path.exists(output_show_note) and os.path.exists(output_transcript):
                    print("Create Show Note")
                    transcript = "\n".join(map(lambda x: x.content, read_srt(output_transcript)))
                    show_note, _ = shownote.create_show_note(transcript, self.podcast_meta["description"])
                    Path(output_show_note).write_text(show_note)
                    logger.debug(f"Show Note Path:{output_show_note.absolute().as_uri()}")
                else:
                    print(f"Show Note Exists: {output_show_note}")
            else:
                print("No Description")

            if os.path.exists(output_show_note):
                self.podcast_meta["description"] = Path(output_show_note).read_text()
                self.podcast_meta["memo_path"] = output_show_note

        self.podcast_meta["episode_number"] = publish_index
        self.podcast_meta["transcript"] = conf.tool_output("stt.srt").read_text()
        self.podcast_meta["title"] = title
        self.podcast_meta["title_path"] = conf.tool_output("title.txt")
        self.podcast_meta["n_txt_file"] = n_txt_file

        # update ui
        self.title_text.value = title
        await self.update_async()

    async def publish_to_podcast(self, e):
        """
        ポッドキャストを配信&SNS,ブログに投稿する
        :param e:
        :return:
        """
        if self.output_file is None:
            print("Not Found Publish File")
            return

        is_draft = os.getenv("APP_PUBLISH_DRAFT", "False").lower() == "true"
        skip_publish = os.getenv("APP_SKIP_PUBLISH_PODCAST", "False").lower() == "true"
        logger.debug(f"Publish is Draft?: {is_draft}")
        publish_conf = read_preset(self.publish_select.value, os.environ["APP_PUBLISH_PRESET_DIR"])

        thumbnail = publish_conf["publish"]["thumbnail"] if "thumbnail" in publish_conf.get("publish", {}) else None
        try:
            if not skip_publish:
                logger.info("Launch Publish Browser")
                share_url = await sfp_uploader.publish(
                    os.environ["PODCAST_URL"],
                    os.environ["PODCAST_EMAIL"],
                    os.environ["PODCAST_PASSWORD"],
                    os.path.abspath(self.output_file),
                    Path(self.podcast_meta["title_path"]).read_text(),
                    markdown.markdown(text=Path(self.podcast_meta["memo_path"]).read_text(),
                                      extensions=["mdx_linkify"]),
                    is_html=True,
                    timeout=720 * 1000,  # 出すまでに時間がかかるので、長めに取っておく。720秒
                    thumbnail=thumbnail,
                    is_publish=not is_draft,

                )
            else:
                logger.debug("APP_SKIP_PUBLISH_PODCAST is True, Skip Publish")
                share_url = "https://open.spotify.com/episode/5iGKnrVneoKaAHWtXIglW6"
            self.podcast_meta["share_url"] = share_url
            categories = create_blog_categories.create(self.podcast_meta["transcript"])
            blog_title = f"ポッドキャスト-とにかくヨシ!-第{self.podcast_meta['episode_number']:04d}回 {self.podcast_meta['title']} アーカイブ"
            stt_label_map: List[Dict] = publish_conf["speak"]["labels"]
            label_name_map: Dict[str, str] = {e["id"]: e["name"] for e in stt_label_map}

            publish_map: Dict[str, Dict] = {e["id"]: e for e in stt_label_map}
            template_file = "zunda_w/apis/hatena/hatena_comment_with_avatar.html"
            blog_transcription = srt_as_interview_blog_content(self.podcast_meta["transcript"],
                                                               template_file,
                                                               label_name_map,
                                                               publish_map)
            # srt_as_blog_content(self.podcast_meta["transcript"], label_name_map)
            result = await share(share_url, retry=10,
                                 blog_template=os.environ["HATENA_BLOG_TEMPLATE_MD"],
                                 blog_template_kwargs={
                                     "episode_number": self.podcast_meta["episode_number"],
                                     "blog_title": blog_title,
                                     "categories": categories,
                                     "show_note": self.podcast_meta["description"],
                                     "transcript": blog_transcription
                                 },
                                 draft=is_draft)

            logger.info(result)
            logger.success("Publish Success")
            # Post process
            increment_file(self.podcast_meta["n_txt_file"])
        except Exception as e:
            logger.exception(e)
            print(e)
        await self.update_async()

    async def update_progress(self, status: bool):
        self.is_convert = status
        self.progress.visible = status
        await self.update_async()

    async def set_file_as_output(self, e):
        files = list(map(lambda x: x.path, self.audio_files.controls))
        if len(files) != 1:
            logger.warning("Select First one file for output")
        self.output_file = files[0]
        logger.info(f"Set Output File:{self.output_file}")
        self.publish_button.visible = True
        await self.update_async()

    async def task_convert(self, files, preset: str, publish_preset: str):
        """ポッドキャストの音声を変換(タスク)"""
        output_dir = Path(self.output_dir.value)
        try:
            output_file, error = convert(files, preset, publish_preset, str(output_dir), self.OUTPUT_ROOT_DIR)
            if error:
                await self.update_progress(False)
                return
            self.output_file = output_file
        except Exception as e:
            logger.exception(e)
            self.is_convert = False
            await self.update_progress(False)
            await self.update_async()
            return
        self.progress.visible = False
        self.is_convert = False
        self.publish_button.visible = True
        await self.update_async()

    async def convert(self, e):
        """ポッドキャストの音声を変換"(UI Event)"""
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
    page.title = os.environ.get("APP_TITLE", "Podcast Studio")
    page.show_semantics_debugger = False
    page.window_visible = True
    page.window_width = 800
    page.window_height = 850

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.ADAPTIVE

    # create app control and add it to the page
    await page.add_async(ConverterApp(default_preset=presets, publish_presets=publish_preset))


def __main__():
    ft.app(main, view=ft.AppView.FLET_APP_HIDDEN)
