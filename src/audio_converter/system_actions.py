import ctypes
import logging
import os
import platform
import subprocess
import time
from pathlib import Path

try:
    import psutil
except Exception:  # pragma: no cover - optional dependency
    psutil = None


def set_low_priority_current_process(enable: bool) -> None:
    if not enable:
        return

    system = platform.system().lower()

    try:
        if psutil is not None:
            proc = psutil.Process(os.getpid())
            if system == "windows":
                proc.nice(psutil.IDLE_PRIORITY_CLASS)
            else:
                proc.nice(19)
        else:
            # psutil がない環境でも標準ライブラリのみで優先度を下げる
            if system == "windows":
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"$p=Get-Process -Id {os.getpid()}; $p.PriorityClass='Idle'",
                    ],
                    check=False,
                )
            else:
                os.nice(19)
        logging.info("低優先度モードを有効化しました。")
    except Exception as exc:
        logging.warning("低優先度モードの設定に失敗: %s", exc)


def open_folder(path: Path) -> None:
    system = platform.system().lower()
    try:
        if system == "windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif system == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as exc:
        logging.warning("フォルダを開けませんでした: %s", exc)


def sleep_after_delay(seconds: int = 60) -> None:
    logging.info("%s秒後にスリープを試行します。", seconds)
    time.sleep(seconds)

    system = platform.system().lower()
    try:
        if system == "windows":
            ctypes.windll.powrprof.SetSuspendState(False, True, False)
        elif system == "darwin":
            subprocess.run(["pmset", "sleepnow"], check=False)
        else:
            subprocess.run(["systemctl", "suspend"], check=False)
    except Exception as exc:
        logging.warning("スリープの実行に失敗: %s", exc)
