from pathlib import Path

PROJECT_DIRS = [
    "bin",
    "fonts",
    "logs",
    "01_Input",
    "02_Processing",
    "03_Output",
]

AUDIO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".flac",
    ".aac",
    ".m4a",
    ".alac",
    ".ogg",
    ".aiff",
    ".aif",
    ".wma",
    ".opus",
}

DEFAULT_VIDEO_WIDTH = 1920
DEFAULT_VIDEO_HEIGHT = 1080
DEFAULT_VIDEO_FPS = 60
DEFAULT_AUDIO_BITRATE = "320k"
DEFAULT_LOG_LEVEL = "INFO"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]
