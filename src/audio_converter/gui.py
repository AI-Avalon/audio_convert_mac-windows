import asyncio

import flet as ft

from .bootstrap import ensure_fonts_extracted, ensure_project_dirs, ensure_ffmpeg
from .constants import project_root
from .engine import run_conversion, list_input_audio_files
from .logging_utils import setup_logging
from .system_actions import open_folder, set_low_priority_current_process, sleep_after_delay


async def build_and_run(page: ft.Page) -> None:
    root = project_root()
    ensure_project_dirs(root)
    ensure_fonts_extracted(root)
    setup_logging(root)

    page.title = "Universal Audio Visualizer"
    page.padding = 20
    page.window_width = 960
    page.window_height = 780
    page.scroll = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0F1218"
    
    # ウィンドウアイコン（データURIで簡単なアイコン）
    try:
        page.window_icon = "icons/icon.png"
    except Exception:
        pass  # アイコン設定に失敗しても続行

    # UI コンポーネント定義
    status = ft.Text("待機中", size=16, color="#F2F4F8")
    progress = ft.ProgressBar(width=900, value=0, color="#F97316", bgcolor="#263245")
    logs = ft.TextField(
        label="進捗ログ",
        multiline=True,
        min_lines=10,
        max_lines=18,
        read_only=True,
        text_style=ft.TextStyle(size=11, font_family="Consolas"),
    )
    file_counter = ft.Text("対象ファイル: 0 / 0", size=14, color="#C9D3E2")
    ratio_text = ft.Text("進捗: 0%", size=14, color="#C9D3E2")
    estimated_time = ft.Text("推定処理時間: 計算中...", size=13, color="#A0AEC0")
    
    # 音源リスト表示
    audio_list = ft.Column(controls=[], scroll=ft.ScrollMode.AUTO)
    audio_list_container = ft.Container(
        content=audio_list,
        bgcolor="#1A2332",
        border_radius=8,
        padding=10,
        height=150,
    )
    audio_list_header = ft.Text("認識された音源ファイル:", size=13, weight=ft.FontWeight.BOLD, color="#E0E7FF")

    low_priority = ft.Checkbox(label="低優先度モード", value=True)
    open_after = ft.Checkbox(label="完了後に出力フォルダを開く", value=True)
    sleep_after = ft.Checkbox(label="完了1分後にスリープ", value=False)
    force_ffmpeg = ft.Checkbox(label="FFmpegを再ダウンロード", value=False)
    merge_all = ft.Checkbox(label="全音源を結合した動画も生成", value=False)

    def refresh_audio_list():
        """認識された音源リストを更新"""
        input_dir = root / "01_Input"
        files = list_input_audio_files(input_dir)
        
        audio_list.controls.clear()
        if files:
            total_duration = 0.0
            ffmpeg_path = root / "bin" / "ffmpeg"
            ffprobe_path = ffmpeg_path.with_name("ffprobe")
            
            for file in files:
                # ファイル名表示
                duration_str = ""
                try:
                    # 簡易的に処理時間を推定（ファイルサイズから）
                    size_mb = file.stat().st_size / (1024 * 1024)
                    # 粗い推定：1MB あたり約0.1秒エンコード（実際には動画の長さに依存）
                    estimated_sec = size_mb * 0.3
                    total_duration += estimated_sec
                    minutes = int(estimated_sec) // 60
                    seconds = int(estimated_sec) % 60
                    duration_str = f" (~{minutes}m{seconds}s)"
                except Exception:
                    pass
                
                item_text = ft.Text(
                    f"• {file.name}{duration_str}",
                    size=12,
                    color="#D0D8E0",
                    overflow=ft.TextOverflow.ELLIPSIS,
                )
                audio_list.controls.append(item_text)
            
            # 合計処理時間を推定
            total_minutes = int(total_duration) // 60
            total_seconds = int(total_duration) % 60
            estimated_time.value = f"推定処理時間: {total_minutes}m{total_seconds}s（{len(files)}ファイル）"
        else:
            audio_list.controls.append(
                ft.Text("01_Input フォルダに音源ファイルが見つかりません", size=12, color="#888A8E", italic=True)
            )
            estimated_time.value = "推定処理時間: -"
        
        page.update()

    async def refresh_clicked(_):
        """リスト更新ボタンのコールバック"""
        await asyncio.to_thread(refresh_audio_list)

    refresh_button = ft.ElevatedButton(
        "更新",
        on_click=refresh_clicked,
        width=100,
        height=40,
    )
    refresh_button.style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=8),
        padding=ft.Padding(10, 8, 10, 8),
    )

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
            merge_all.value,
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
        await asyncio.to_thread(refresh_audio_list)  # 完了後にリストを更新
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
                ft.Text("UNIVERSAL AUDIO VISUALIZER", size=14, weight=ft.FontWeight.W_600, color="#FDBA74"),
                ft.Text("ユニバーサル・オーディオビジュアライザー", size=32, weight=ft.FontWeight.BOLD, color="#F8FAFC"),
                ft.Text("演奏会品質のスペクトラム映像を、安定したローカル実行で生成", size=14, color="#D5DFED"),
                ft.Text(f"プロジェクトルート: {root}", size=12, color="#A8B7CC"),
            ],
            spacing=6,
        ),
    )

    # 初期化時に音源リストを読み込み
    await asyncio.to_thread(refresh_audio_list)

    page.add(
        ft.Column(
            [
                title_panel,
                ft.Row([low_priority, open_after, sleep_after, force_ffmpeg, merge_all], wrap=True),
                ft.Row([run_button, refresh_button], spacing=10),
                status,
                progress,
                ft.Row([file_counter, ratio_text], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                estimated_time,
                audio_list_header,
                audio_list_container,
                logs,
            ],
            spacing=12,
        )
    )


def launch_gui() -> None:
    ft.app(target=build_and_run)
