"""
bacs/loader.py
devices.json 을 읽어 BacsDevice 리스트로 변환
- load_devices(path) : JSON 파일 경로를 받아 list[BacsDevice] 반환
"""
from __future__ import annotations

import json
from pathlib import Path

from bacs.models import BacsDevice


def load_devices(path: str | Path) -> list[BacsDevice]:
    """
    devices.json 파일을 읽어 BacsDevice 리스트로 변환한다.

    Args:
        path: devices.json 파일 경로 (str 또는 Path)

    Returns:
        list[BacsDevice] — 등록된 장비 목록

    Raises:
        FileNotFoundError : 파일이 존재하지 않을 때
        json.JSONDecodeError : JSON 형식이 올바르지 않을 때
        KeyError : "devices" 키가 없을 때
    """
    path = Path(path)

    # 파일 읽기 (없으면 FileNotFoundError 전파)
    text = path.read_text(encoding="utf-8")

    # JSON 파싱 (형식 오류 시 JSONDecodeError 전파)
    data = json.loads(text)

    # 각 항목을 BacsDevice 로 변환 (port 없으면 기본값 7788 적용)
    return [BacsDevice(**item) for item in data["devices"]]
