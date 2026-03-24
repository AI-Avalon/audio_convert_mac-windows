import asyncio

import flet as ft

from .bootstrap import ensure_project_dirs
from .constants import project_root
from .engine import run_conversion
from .logging_utils import setup_logging
from .system_actions import open_folder, set_low_priority_current_process, sleep_after_delay


async def build_and_run(page: ft.Page) -> None:
    root = project_root()
    ensure_project_dirs(root)
    setup_logging(root)

    page.title = "Universal Audio Visualizer"
    page.padding = 20
    page.window_width = 920
    page.window_height = 680
    page.scroll = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0F1218"

    status = ft.Text("待機中", size=16, color="#F2F4F8")
    progress = ft.ProgressBar(width=860, value=0, color="#F97316", bgcolor="#263245")
    logs = ft.TextField(
        label="進捗ログ",
        multiline=True,
        min_lines=12,
        max_lines=20,
        read_only=True,
        text_style=ft.TextStyle(size=12, font_family="Consolas"),
    )
    file_counter = ft.Text("対象ファイル: 0 / 0", size=14, color="#C9D3E2")
    ratio_text = ft.Text("進捗: 0%", size=14, color="#C9D3E2")

    low_priority = ft.Checkbox(label="低優先度モード", value=True)
    open_after = ft.Checkbox(label="完了後に出力フォルダを開く", value=True)
    sleep_after = ft.Checkbox(label="完了1分後にスリープ", value=False)
    force_ffmpeg = ft.Checkbox(label="FFmpegを再ダウンロード", value=False)

    async def run_clicked(_):
        run_button.disabled = True
        status.value = "初期化中..."
        logs.value = ""
        progress.value = 0
        file_counter.value = "対象ファイル: 0 / 0"
        ratio_text.value = "進捗: 0%"
        page.update()

        set_low_priority_current_process(low_priority.value)

        def on_progress(done: float, total: int, message: str) -> None:
            def apply_update() -> None:
                total_safe = max(float(total), 1.0)
                ratio = min(max(done / total_safe, 0.0), 1.0)
                progress.value = ratio
                status.value = message
                file_counter.value = f"対象ファイル: {min(int(done) + 1, total) if total > 0 else 0} / {total}"
                ratio_text.value = f"進捗: {int(ratio * 100)}%"
                lines = logs.value.splitlines()
                lines.append(message)
                logs.value = "\n".join(lines[-300:])
                page.update()

            page.call_from_thread(apply_update)

        result = await asyncio.to_thread(
            run_conversion,
            root,
            force_ffmpeg.value,
            on_progress,
        )

        status.value = (
            f"完了: 成功 {result.success} / 失敗 {result.failed} / 合計 {result.total}"
        )
        progress.value = 1 if result.total > 0 else 0
        ratio_text.value = "進捗: 100%" if result.total > 0 else "進捗: 0%"
        logs.value += f"出力先: {result.output_dir}\n"
        page.update()

        if open_after.value:
            open_folder(result.output_dir)

        if sleep_after.value:
            await asyncio.to_thread(sleep_after_delay, 60)

        run_button.disabled = False
        page.update()

    run_button = ft.ElevatedButton("変換開始", on_click=run_clicked)
    run_button.style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=12),
        padding=ft.Padding(22, 16, 22, 16),
    )

    title_panel = ft.Container(
        padding=18,
        border_radius=16,
        gradient=ft.LinearGradient(colors=["#1B2333", "#11263D", "#3A1E13"], begin=ft.alignment.top_left, end=ft.alignment.bottom_right),
        content=ft.Column(
            [
                ft.Text("UNIVERSAL AUDIO VISUALIZER", size=14, weight=ft.FontWeight.W_600, color="#FDBA74", letter_spacing=1.6),
                ft.Text("ユニバーサル・オーディオビジュアライザー", size=32, weight=ft.FontWeight.BOLD, color="#F8FAFC"),
                ft.Text("演奏会品質のスペクトラム映像を、安定したローカル実行で生成", size=14, color="#D5DFED"),
                ft.Text(f"プロジェクトルート: {root}", size=12, color="#A8B7CC"),
            ],
            spacing=6,
        ),
    )

    page.add(
        ft.Column(
            [
                title_panel,
                ft.Row([low_priority, open_after, sleep_after, force_ffmpeg], wrap=True),
                run_button,
                status,
                progress,
                ft.Row([file_counter, ratio_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                logs,
            ],
            spacing=14,
        )
    )


def launch_gui() -> None:
    ft.app(target=build_and_run)
