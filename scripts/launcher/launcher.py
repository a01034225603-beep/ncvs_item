"""
NCVS Windows 트레이 런처
────────────────────────
- 시스템 트레이 아이콘으로 서버 기동/중지 관리
- 백엔드(uvicorn :8000) + 프론트엔드(node :3000) 프로세스 제어
- 아이콘 색상: 초록(RUNNING) / 빨강(STOPPED)

의존: pystray, pillow
빌드: PyInstaller --onefile launcher.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import threading
import webbrowser
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

# ── 경로 설정 ────────────────────────────────────────────────────────────────
# PyInstaller 번들 기준 또는 스크립트 기준 루트 경로
if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent  # NCVS_Setup.exe 설치 경로
else:
    ROOT = Path(__file__).resolve().parent.parent.parent  # 개발 시 repo 루트

PYTHON_EXE = ROOT / "python" / "python.exe"
NODE_EXE = ROOT / "node" / "node.exe"
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

# ── 아이콘 생성 (PIL 동적 생성 — 외부 .ico 불필요) ──────────────────────────
def _make_icon(color: str) -> Image.Image:
    """64×64 원형 아이콘 생성"""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=color, outline="#ffffff", width=3)
    return img


ICON_GREEN = _make_icon("#22c55e")   # 서버 실행 중
ICON_RED   = _make_icon("#ef4444")   # 서버 중지
ICON_YELLOW = _make_icon("#f59e0b")  # 시작/중지 중


# ── 프로세스 관리 ────────────────────────────────────────────────────────────
class ServerManager:
    def __init__(self) -> None:
        self._backend:  subprocess.Popen | None = None
        self._frontend: subprocess.Popen | None = None
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        with self._lock:
            return (
                self._backend is not None and self._backend.poll() is None
                and self._frontend is not None and self._frontend.poll() is None
            )

    def start(self, on_progress: callable | None = None) -> None:
        """백엔드 → 프론트엔드 순으로 기동"""
        with self._lock:
            if self.is_running:
                return

            env = os.environ.copy()
            env["DATABASE_URL"] = f"sqlite+aiosqlite:///{ROOT / 'data' / 'ncvs.db'}"
            env["JWT_SECRET"]   = _load_env_value("JWT_SECRET", "change-me-32-chars-minimum!!")

            # 백엔드 기동
            if on_progress:
                on_progress("백엔드 시작 중...")
            self._backend = subprocess.Popen(
                [str(PYTHON_EXE), "-m", "uvicorn", "app.main:app",
                 "--host", "0.0.0.0", "--port", "8000", "--log-level", "warning"],
                cwd=str(BACKEND_DIR),
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

            # 백엔드 기동 대기 (최대 10초)
            for _ in range(20):
                time.sleep(0.5)
                if _port_open(8000):
                    break

            # 프론트엔드 기동
            if on_progress:
                on_progress("프론트엔드 시작 중...")
            fe_env = env.copy()
            fe_env["PORT"] = "3000"
            fe_env["NEXT_PUBLIC_API_URL"] = BACKEND_URL
            self._frontend = subprocess.Popen(
                [str(NODE_EXE), str(FRONTEND_DIR / "server.js")],
                cwd=str(FRONTEND_DIR),
                env=fe_env,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

    def stop(self, on_progress: callable | None = None) -> None:
        """프론트엔드 → 백엔드 순으로 종료"""
        with self._lock:
            if on_progress:
                on_progress("서버 중지 중...")
            for proc in (self._frontend, self._backend):
                if proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            self._backend = None
            self._frontend = None


# ── 유틸 ─────────────────────────────────────────────────────────────────────
def _port_open(port: int) -> bool:
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def _load_env_value(key: str, default: str) -> str:
    """ROOT/.env 파일에서 값 읽기"""
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip()
    return default


# ── 트레이 앱 ────────────────────────────────────────────────────────────────
class TrayApp:
    def __init__(self) -> None:
        self.mgr = ServerManager()
        self.icon = pystray.Icon(
            name="NCVS",
            icon=ICON_RED,
            title="NCVS — 서버 중지",
            menu=self._build_menu(),
        )

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("▶  서버 시작", self._on_start,
                             enabled=lambda _: not self.mgr.is_running),
            pystray.MenuItem("■  서버 중지", self._on_stop,
                             enabled=lambda _: self.mgr.is_running),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("🌐 브라우저 열기", self._on_open_browser,
                             enabled=lambda _: self.mgr.is_running),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("✕  종료", self._on_quit),
        )

    # ── 이벤트 핸들러 ────────────────────────────────────────────────────────
    def _on_start(self) -> None:
        def _task():
            self.icon.icon = ICON_YELLOW
            self.icon.title = "NCVS — 시작 중..."
            self.mgr.start()
            if self.mgr.is_running:
                self.icon.icon = ICON_GREEN
                self.icon.title = "NCVS — 실행 중"
                # 시작 성공 시 브라우저 자동 오픈
                webbrowser.open(FRONTEND_URL)
            else:
                self.icon.icon = ICON_RED
                self.icon.title = "NCVS — 시작 실패"
        threading.Thread(target=_task, daemon=True).start()

    def _on_stop(self) -> None:
        def _task():
            self.icon.icon = ICON_YELLOW
            self.icon.title = "NCVS — 중지 중..."
            self.mgr.stop()
            self.icon.icon = ICON_RED
            self.icon.title = "NCVS — 서버 중지"
        threading.Thread(target=_task, daemon=True).start()

    def _on_open_browser(self) -> None:
        webbrowser.open(FRONTEND_URL)

    def _on_quit(self) -> None:
        self.mgr.stop()
        self.icon.stop()

    # ── 실행 ─────────────────────────────────────────────────────────────────
    def run(self) -> None:
        # 앱 시작 시 서버 자동 기동
        threading.Thread(target=self._on_start, daemon=True).start()
        self.icon.run()


# ── 엔트리포인트 ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    TrayApp().run()
