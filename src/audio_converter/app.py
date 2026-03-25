import argparse
import logging
from pathlib import Path

from .bootstrap import ensure_project_dirs
from .constants import project_root
from .engine import run_conversion
from .logging_utils import setup_logging
from .system_actions import open_folder, set_low_priority_current_process, sleep_after_delay


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Universal Audio Visualizer")
    parser.add_argument("--gui", action="store_true", help="Flet GUIで起動する")
    parser.add_argument("--init-only", action="store_true", help="初期化のみ実行する")
    parser.add_argument("--force-download", action="store_true", help="FFmpeg再取得")
    parser.add_argument("--low-priority", action="store_true", help="低優先度で実行")
    parser.add_argument(
        "--no-open-folder",
        action="store_true",
        help="完了後に出力フォルダを開かない",
    )
    parser.add_argument("--sleep-after", action="store_true", help="完了後1分でスリープ")
    parser.add_argument("--merge-all", action="store_true", help="入力音源を1本に結合した動画も生成")
    return parser.parse_args()


def run_cli(root: Path, args: argparse.Namespace) -> int:
    if args.low_priority:
        set_low_priority_current_process(True)

    result = run_conversion(
        root=root,
        force_ffmpeg_download=args.force_download,
        merge_all_inputs=args.merge_all,
    )

    logging.info("変換結果: success=%s failed=%s total=%s", result.success, result.failed, result.total)

    if not args.no_open_folder:
        open_folder(result.output_dir)

    if args.sleep_after:
        sleep_after_delay(60)

    return 0 if result.failed == 0 else 1


def main() -> int:
    root = project_root()
    ensure_project_dirs(root)
    setup_logging(root)

    args = parse_args()

    if args.gui:
        try:
            from .gui import launch_gui

            launch_gui()
            return 0
        except Exception as exc:
            logging.warning("GUI起動に失敗したためCLIへフォールバックします: %s", exc)
            return run_cli(root, args)

    if args.init_only:
        from .bootstrap import ensure_ffmpeg

        ensure_ffmpeg(root, force=args.force_download)
        logging.info("初期化のみ完了")
        return 0

    return run_cli(root, args)
