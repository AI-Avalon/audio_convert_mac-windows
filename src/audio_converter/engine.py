import datetime as dt
import json
import logging
import shutil
import subprocess
import time
from collections import deque
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


def _build_work_path(processing_dir: Path, idx: int, source: Path) -> Path:
    safe_name = source.name.replace("/", "_").replace("\\", "_")
    return processing_dir / f"{idx:04d}_{safe_name}"


def _archive_original(input_dir: Path, archive_run_dir: Path, source: Path) -> None:
    relative = source.relative_to(input_dir)
    target = archive_run_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)

    stem = target.stem
    suffix = target.suffix
    counter = 1
    while target.exists():
        target = target.with_name(f"{stem}_{counter}{suffix}")
        counter += 1

    shutil.move(str(source), str(target))
    logging.info("入力ファイルをアーカイブへ移動: %s -> %s", source, target)


def _cleanup_empty_dirs(root_dir: Path) -> None:
    dirs = sorted((p for p in root_dir.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True)
    for path in dirs:
        try:
            if not any(path.iterdir()):
                path.rmdir()
        except Exception:
            pass


def _resolve_ffprobe_path(ffmpeg_path: Path) -> Path:
    name = "ffprobe.exe" if ffmpeg_path.name.lower().endswith(".exe") else "ffprobe"
    return ffmpeg_path.with_name(name)


def _probe_duration_seconds(ffprobe_path: Path, source: Path) -> float | None:
    if not ffprobe_path.exists():
        return None

    command = [
        str(ffprobe_path),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(source),
    ]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=20)
        if proc.returncode != 0:
            return None
        payload = json.loads(proc.stdout)
        duration = payload.get("format", {}).get("duration")
        if duration is None:
            return None
        value = float(duration)
        return value if value > 0 else None
    except Exception:
        return None


def _timecode_to_seconds(value: str) -> float:
    hh, mm, ss = value.split(":")
    return int(hh) * 3600 + int(mm) * 60 + float(ss)


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


def convert_one_file(
    root: Path,
    ffmpeg_path: Path,
    source: Path,
    output_dir: Path,
    progress_detail_cb=None,
) -> tuple[bool, Path]:
    output_file = _build_output_path(output_dir, source)
    ffprobe_path = _resolve_ffprobe_path(ffmpeg_path)
    duration_sec = _probe_duration_seconds(ffprobe_path, source)

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
        "-progress",
        "pipe:1",
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

    if progress_detail_cb and duration_sec:
        progress_detail_cb(0.0, duration_sec, f"エンコード開始: {source.name}")

    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    tail_lines: deque[str] = deque(maxlen=200)
    last_emit = 0.0
    if proc.stdout is not None:
        for raw_line in proc.stdout:
            line = raw_line.strip()
            if not line:
                continue
            tail_lines.append(line)

            if progress_detail_cb and duration_sec:
                now = time.monotonic()
                current = None
                if line.startswith("out_time_ms="):
                    try:
                        current = float(line.split("=", 1)[1]) / 1_000_000.0
                    except Exception:
                        current = None
                elif line.startswith("out_time="):
                    try:
                        current = _timecode_to_seconds(line.split("=", 1)[1])
                    except Exception:
                        current = None

                if current is not None and (now - last_emit >= 0.5):
                    progress_detail_cb(
                        min(max(current, 0.0), duration_sec),
                        duration_sec,
                        f"エンコード中: {source.name}",
                    )
                    last_emit = now

    return_code = proc.wait()

    if return_code != 0:
        logging.error("変換失敗: %s", source)
        logging.error("FFmpeg出力(末尾):\n%s", "\n".join(tail_lines))
        return False, output_file

    if progress_detail_cb and duration_sec:
        progress_detail_cb(duration_sec, duration_sec, f"エンコード完了: {source.name}")

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
    archive_root = root / "04_Archive"

    run_stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    run_dir = output_root / run_stamp
    archive_run_dir = archive_root / run_stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    archive_run_dir.mkdir(parents=True, exist_ok=True)

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

        work_src = _build_work_path(processing_dir, idx, src)
        try:
            shutil.copy2(src, work_src)
            if progress_cb:
                progress_cb(idx - 1, total, f"解析中: {src.name}")

            def _detail(current: float, duration: float, message: str) -> None:
                if not progress_cb:
                    return
                if duration <= 0:
                    progress_cb(idx - 1, total, message)
                    return
                file_ratio = min(max(current / duration, 0.0), 1.0)
                overall = (idx - 1) + file_ratio
                progress_cb(overall, total, message)

            ok, _ = convert_one_file(root, ffmpeg_path, work_src, run_dir, _detail)
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

            try:
                _archive_original(input_dir, archive_run_dir, src)
            except Exception as exc:
                logging.exception("アーカイブ移動に失敗: %s", exc)

        if progress_cb:
            progress_cb(idx, total, f"完了: {src.name}")

    for child in processing_dir.iterdir():
        if child.is_file() and child.name != ".gitkeep":
            child.unlink(missing_ok=True)

    _cleanup_empty_dirs(input_dir)

    return ConversionResult(total=total, success=success, failed=failed, output_dir=run_dir)
