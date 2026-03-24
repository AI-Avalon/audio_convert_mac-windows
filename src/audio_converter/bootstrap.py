import argparse
import datetime as dt
import logging
import os
import platform
import shutil
import stat
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path


PROJECT_DIRS = [
    "bin",
    "fonts",
    "logs",
    "01_Input",
    "02_Processing",
    "03_Output",
]

FFMPEG_TARGET = "ffmpeg"


def setup_logging(root: Path) -> Path:
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d")
    log_path = logs_dir / f"converter_{stamp}.log"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(sh)

    return log_path


def ensure_project_dirs(root: Path) -> None:
    for rel in PROJECT_DIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)

    processing_keep = root / "02_Processing" / ".gitkeep"
    if not processing_keep.exists():
        processing_keep.write_text("", encoding="utf-8")

    archive_keep = root / "04_Archive" / ".gitkeep"
    if not archive_keep.exists():
        archive_keep.write_text("", encoding="utf-8")


def _choose_ffmpeg_source() -> tuple[str, str]:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        return (
            "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
            "zip",
        )

    if system == "darwin":
        if machine in {"arm64", "aarch64"}:
            return ("https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip", "zip")
        return ("https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip", "zip")

    raise RuntimeError(f"Unsupported OS: {system}")


def _find_ffmpeg_in_dir(search_root: Path) -> Path | None:
    exe_name = "ffmpeg.exe" if platform.system().lower() == "windows" else "ffmpeg"
    candidates = list(search_root.rglob(exe_name))
    if not candidates:
        return None

    candidates.sort(key=lambda p: len(p.parts))
    return candidates[0]


def _download_file(url: str, target: Path) -> None:
    with urllib.request.urlopen(url) as resp, target.open("wb") as out:
        shutil.copyfileobj(resp, out)


def _extract_archive(archive_path: Path, extract_to: Path, kind: str) -> None:
    if kind == "zip":
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(extract_to)
        return

    if kind == "tar.xz":
        with tarfile.open(archive_path, "r:xz") as tf:
            tf.extractall(extract_to)
        return

    raise RuntimeError(f"Unsupported archive kind: {kind}")


def ensure_ffmpeg(root: Path, force: bool = False) -> Path:
    bin_dir = root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_name = "ffmpeg.exe" if platform.system().lower() == "windows" else "ffmpeg"
    ffmpeg_path = bin_dir / ffmpeg_name

    if ffmpeg_path.exists() and not force:
        logging.info("FFmpeg already exists: %s", ffmpeg_path)
        return ffmpeg_path

    url, kind = _choose_ffmpeg_source()
    logging.info("Downloading FFmpeg from: %s", url)

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        archive_name = "ffmpeg.zip" if kind == "zip" else "ffmpeg.tar.xz"
        archive_path = tmp_dir / archive_name
        extract_path = tmp_dir / "extract"
        extract_path.mkdir(parents=True, exist_ok=True)

        _download_file(url, archive_path)
        _extract_archive(archive_path, extract_path, kind)

        found = _find_ffmpeg_in_dir(extract_path)
        if found is None:
            raise RuntimeError("Downloaded archive does not contain ffmpeg binary")

        shutil.copy2(found, ffmpeg_path)

    if platform.system().lower() != "windows":
        mode = ffmpeg_path.stat().st_mode
        ffmpeg_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    logging.info("FFmpeg ready: %s", ffmpeg_path)
    return ffmpeg_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap utility for Universal Audio Visualizer"
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Force re-download of FFmpeg even if already present.",
    )
    parser.add_argument(
        "--init-only",
        action="store_true",
        help="Only initialize folders and FFmpeg. No conversion is executed.",
    )
    return parser.parse_args()


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    args = parse_args()

    log_path = setup_logging(root)
    logging.info("Initialization started at root: %s", root)

    try:
        ensure_project_dirs(root)
        ffmpeg_path = ensure_ffmpeg(root, force=args.force_download)
        logging.info("Initialization complete. ffmpeg=%s", ffmpeg_path)
        logging.info("Log file: %s", log_path)

        if not args.init_only:
            logging.info("Note: conversion pipeline is planned for next steps.")

        return 0
    except Exception as exc:
        logging.exception("Initialization failed: %s", exc)
        return 1


__all__ = [
    "ensure_project_dirs",
    "ensure_ffmpeg",
    "main",
]
