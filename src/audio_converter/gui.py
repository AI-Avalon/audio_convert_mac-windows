import asyncio
from pathlib import Path

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
    page.window_width = 920
    page.window_height = 680
    page.scroll = ft.ScrollMode.AUTO

    status = ft.Text("待機中", size=16)
    progress = ft.ProgressBar(width=800, value=0)
    logs = ft.TextField(label="進捗ログ", multiline=True, min_lines=12, max_lines=20, read_only=True)

    low_priority = ft.Checkbox(label="低優先度モード", value=True)
    open_after = ft.Checkbox(label="完了後に出力フォルダを開く", value=True)
    sleep_after = ft.Checkbox(label="完了1分後にスリープ", value=False)
    force_ffmpeg = ft.Checkbox(label="FFmpegを再ダウンロード", value=False)

    async def run_clicked(_):
        run_button.disabled = True
        status.value = "初期化中..."
        logs.value = ""
        progress.value = 0
        page.update()

        set_low_priority_current_process(low_priority.value)

        def on_progress(done: int, total: int, message: str) -> None:
            total_safe = max(total, 1)
            progress.value = done / total_safe
            status.value = message
            logs.value += f"{message}\n"

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
        logs.value += f"出力先: {result.output_dir}\n"
        page.update()

        if open_after.value:
            open_folder(result.output_dir)

        if sleep_after.value:
            await asyncio.to_thread(sleep_after_delay, 60)

        run_button.disabled = False
        page.update()

    run_button = ft.ElevatedButton("変換開始", on_click=run_clicked)

    page.add(
        ft.Column(
            [
                ft.Text("ユニバーサル・オーディオビジュアライザー", size=28, weight=ft.FontWeight.BOLD),
                ft.Text(f"プロジェクトルート: {root}"),
                ft.Row([low_priority, open_after, sleep_after, force_ffmpeg], wrap=True),
                run_button,
                status,
                progress,
                logs,
            ],
            spacing=14,
        )
    )


def launch_gui() -> None:
    ft.app(target=build_and_run)
