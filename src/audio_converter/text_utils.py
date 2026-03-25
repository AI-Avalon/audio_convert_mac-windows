import logging
from pathlib import Path


INVALID_DISPLAY_CHARS = {"\n", "\r", "\t"}


def sanitize_overlay_text(source_name: str, max_len: int = 80) -> tuple[str, bool]:
    changed = False
    buf: list[str] = []
    for ch in source_name:
        if ch in INVALID_DISPLAY_CHARS or (not ch.isprintable()):
            buf.append("_")
            changed = True
        else:
            buf.append(ch)

    text = "".join(buf)
    if len(text) > max_len:
        text = f"{text[: max_len - 3]}..."
        changed = True

    if not text:
        text = "untitled"
        changed = True

    return text, changed


def compute_font_size(text: str) -> int:
    if len(text) > 70:
        return 22
    if len(text) > 55:
        return 26
    if len(text) > 40:
        return 30
    return 34


def escape_drawtext_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace(":", "\\:")
    escaped = escaped.replace("'", "\\'")
    escaped = escaped.replace("%", "\\%")
    escaped = escaped.replace(",", "\\,")
    escaped = escaped.replace("[", "\\[").replace("]", "\\]")
    return escaped


def resolve_font_file(root: Path) -> Path | None:
    fonts_dir = root / "fonts"
    candidates = [
        fonts_dir / "SoukouMincho.ttf",
        fonts_dir / "NotoSansJP-Regular.ttf",
        fonts_dir / "NotoSansCJKjp-Regular.otf",
        fonts_dir / "NotoSansJP-Medium.ttf",
    ]

    for path in candidates:
        if path.exists():
            return path

    for ext in ("*.ttf", "*.otf", "*.ttc"):
        found = list(fonts_dir.glob(ext))
        if found:
            return found[0]

    logging.warning("fonts/ 内にフォントが見つかりません。FFmpegデフォルトフォントを使用します。")
    return None
