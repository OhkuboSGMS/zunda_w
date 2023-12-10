import asyncio

import flet as ft
from flet_core import margin, FilePickerFileType
from omegaconf import OmegaConf


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

    def build(self):
        from zunda_w.constants import update_preset
        update_preset("./preset_config")
        from zunda_w.constants import PRESET_NAME

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
        self.progress = ft.Row(
            visible=False,
            controls=[
                ft.Text("AAAA"),
                ft.ProgressBar(width=400, color="amber", bgcolor="#eeeeee")
            ]
        )
        self.output_dir = ft.TextField(label="OutputDirectory")

        # application's root control (i.e. "view") containing all other controls
        return ft.Column(
            width=600,
            expand=False,
            controls=[
                ft.Row(
                    [ft.Text(value="とにかくヨシ！Studio", style=ft.TextThemeStyle.HEADLINE_MEDIUM)],
                    alignment=ft.MainAxisAlignment.CENTER,
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
            ],
        )

    async def task_convert(self, files, preset):
        from zunda_w import __main__
        from zunda_w.arg import Options
        files = list(filter(lambda x: x is not None, files))
        conf = OmegaConf.structured(Options(audio_files=files, preset=preset))
        if self.output_dir.value:
            conf.target_dir = self.output_dir.value
        __main__._convert(conf)

        self.progress.visible = False
        self.is_convert = False
        await self.update_async()

    async def convert(self, e):
        files = list(map(lambda x: x.path, self.audio_files.controls))
        prest = self.preset_select.value
        print(files, prest)
        self.is_convert = True
        self.progress.visible = True
        await self.update_async()
        asyncio.create_task(self.task_convert(files, prest))

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
