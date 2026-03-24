import datetime as dt
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .bootstrap import ensure_ffmpeg, ensure_project_dirs
from .constants import (
    AUDIO_EXTENSIONS,
    DEFAULT_AUDIO_BITRATE,
    DEFAULT_VIDEO_FPS,
    DEFAULT_VIDEO_HEIGHT,
    DEFAULT_VIDEO_WIDTH,
)
from .text_utils import (
    compute_font_size,
    escape_drawtext_value,
    resolve_font_file,
    sanitize_overlay_text,
)


@dataclass
class ConvertOptions:
    low_priority: bool = False
    open_output_folder: bool = True
    sleep_after_complete: bool = False
    force_ffmpeg_download: bool = False


@dataclass
class ConversionResult:
    total: int
    success: int
    failed: int
    output_dir: Path


def list_input_audio_files(input_dir: Path) -> list[Path]:
    files = [
        p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    ]
    files.sort()
    return files


def _build_output_path(output_dir: Path, source: Path) -> Path:
    safe_stem = source.stem.replace("/", "_").replace("\\", "_").strip()
    if not safe_stem:
        safe_stem = "output"
    return output_dir / f"{safe_stem}.mp4"


def _drawtext_filter(root: Path, source_name: str) -> str:
    text, changed = sanitize_overlay_text(source_name)
    if changed:
        logging.info("ファイル名テロップを安全化: %s -> %s", source_name, text)

    size = compute_font_size(text)
    escaped_text = escape_drawtext_value(text)

    font_file = resolve_font_file(root)
    if font_file is None:
        return (
            "drawtext="
            f"text='{escaped_text}':"
            f"fontcolor=white:fontsize={size}:"
            "box=1:boxcolor=black@0.45:boxborderw=12:"
            "x=w-tw-40:y=h-th-30"
        )

    escaped_font = escape_drawtext_value(str(font_file))
    return (
        "drawtext="
        f"fontfile='{escaped_font}':"
        f"text='{escaped_text}':"
        f"fontcolor=white:fontsize={size}:"
        "box=1:boxcolor=black@0.45:boxborderw=12:"
        "x=w-tw-40:y=h-th-30"
    )


def convert_one_file(root: Path, ffmpeg_path: Path, source: Path, output_dir: Path) -> tuple[bool, Path]:
    output_file = _build_output_path(output_dir, source)

    filter_chain = (
        f"showspectrum=s={DEFAULT_VIDEO_WIDTH}x{DEFAULT_VIDEO_HEIGHT}:"
        "mode=combined:color=fiery:scale=log:slide=scroll:win_func=blackman,"
        "format=yuv420p,"
        + _drawtext_filter(root, source.name)
    )

    command = [
        str(ffmpeg_path),
        "-y",
        "-hide_banner",
        "-nostats",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-filter_complex",
        f"[0:a]{filter_chain}[v]",
        "-map",
        "[v]",
        "-map",
        "0:a",
        "-r",
        str(DEFAULT_VIDEO_FPS),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        DEFAULT_AUDIO_BITRATE,
        "-movflags",
        "+faststart",
        str(output_file),
    ]

    proc = subprocess.run(command, capture_output=True, text=True)

    if proc.returncode != 0:
        logging.error("変換失敗: %s", source)
        logging.error("FFmpeg stderr:\n%s", proc.stderr[-4000:])
        return False, output_file

    logging.info("変換完了: %s", output_file)
    return True, output_file


def run_conversion(
    root: Path,
    force_ffmpeg_download: bool = False,
    progress_cb=None,
) -> ConversionResult:
    ensure_project_dirs(root)
    ffmpeg_path = ensure_ffmpeg(root, force=force_ffmpeg_download)

    input_dir = root / "01_Input"
    processing_dir = root / "02_Processing"
    output_root = root / "03_Output"

    run_dir = output_root / dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    run_dir.mkdir(parents=True, exist_ok=True)

    files = list_input_audio_files(input_dir)
    total = len(files)
    success = 0
    failed = 0

    if total == 0:
        logging.warning("01_Input に変換対象の音源が見つかりません。")
        return ConversionResult(total=0, success=0, failed=0, output_dir=run_dir)

    for idx, src in enumerate(files, start=1):
        if progress_cb:
            progress_cb(idx - 1, total, f"変換中: {src.name}")

        work_src = processing_dir / src.name
        try:
            shutil.copy2(src, work_src)
            ok, _ = convert_one_file(root, ffmpeg_path, work_src, run_dir)
            if ok:
                success += 1
            else:
                failed += 1
        except Exception as exc:
            failed += 1
            logging.exception("変換中に例外発生: %s", exc)
        finally:
            try:
                work_src.unlink(missing_ok=True)
            except Exception:
                pass

        if progress_cb:
            progress_cb(idx, total, f"完了: {src.name}")

    for child in processing_dir.iterdir():
        if child.is_file() and child.name != ".gitkeep":
            child.unlink(missing_ok=True)

    return ConversionResult(total=total, success=success, failed=failed, output_dir=run_dir)
