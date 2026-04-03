from __future__ import annotations

import shutil
import signal
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    python = sys.executable
    npm = shutil.which("npm")
    if npm is None:
        print("npm is required to run desktop app.", file=sys.stderr)
        return 1

    backend_cmd = [python, "run_server.py"]
    desktop_cmd = [npm, "run", "dev"]

    backend = subprocess.Popen(backend_cmd, cwd=ROOT / "backend")
    desktop = subprocess.Popen(desktop_cmd, cwd=ROOT / "desktop")
    processes = [backend, desktop]

    def terminate_all() -> None:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    def handle_signal(signum: int, _frame: object) -> None:
        print(f"Received signal {signum}. Stopping dev processes.")
        terminate_all()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)

    try:
        while True:
            backend_code = backend.poll()
            desktop_code = desktop.poll()
            if backend_code is not None:
                print(f"Backend exited with code {backend_code}")
                terminate_all()
                return backend_code
            if desktop_code is not None:
                print(f"Desktop exited with code {desktop_code}")
                terminate_all()
                return desktop_code
    finally:
        terminate_all()


if __name__ == "__main__":
    raise SystemExit(main())

