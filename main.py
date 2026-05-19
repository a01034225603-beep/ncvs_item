"""
main.py
BACS UDP 헬스체크 실행 진입점

실행 방법:
    python3 main.py
    python3 main.py --devices path/to/devices.json
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from bacs.loader import load_devices
from bacs.models import HealthStatus
from bacs.scheduler import run_all

# 기본 devices.json 경로 (프로젝트 루트 기준)
DEFAULT_DEVICES_PATH = Path(__file__).parent / "devices.json"


def _hex(data: bytes | None, width: int = 16) -> str:
    """bytes 를 보기 좋은 hex 덤프 문자열로 변환"""
    if data is None:
        return "  (없음)"
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        hex_part  = " ".join(f"{b:02X}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"  {i:04X}  {hex_part:<{width*3}}  {ascii_part}")
    return "\n".join(lines)


def _print_results(results, debug: bool = False) -> None:
    """체크 결과를 콘솔에 출력. 항상 송수신 패킷 hex 덤프 포함"""
    from bacs.protocol import REQUEST_PACKET

    print("\n" + "=" * 60)
    print(f"{'장비명':<20} {'IP':<16} {'타입':<8} {'상태':<10} {'지연(ms)'}")
    print("-" * 60)

    for r in results:
        latency = f"{r.latency_ms:.1f}" if r.latency_ms is not None else "-"
        status_label = "🟢 ONLINE" if r.status == HealthStatus.ONLINE else "🔴 OFFLINE"
        print(f"{r.device.name:<20} {r.device.ip:<16} {r.device.network_type:<8} {status_label:<10} {latency}")

        # 송신 패킷
        print(f"\n  [→ 송신 {len(REQUEST_PACKET)}바이트] → {r.device.ip}:{r.device.port}")
        print(_hex(REQUEST_PACKET))

        # 수신 패킷
        if r.raw_response:
            print(f"\n  [← 수신 {len(r.raw_response)}바이트] ← {r.device.ip}:{r.device.port}")
            print(_hex(r.raw_response))
        else:
            print(f"\n  [← 수신] 없음 (타임아웃 또는 네트워크 오류)")
        print("-" * 60)

    print("=" * 60)
    online  = sum(1 for r in results if r.status == HealthStatus.ONLINE)
    offline = sum(1 for r in results if r.status == HealthStatus.OFFLINE)
    print(f"총 {len(results)}대 | ONLINE: {online}대 | OFFLINE: {offline}대\n")


async def main(devices_path: Path, debug: bool = False) -> None:
    """메인 실행 함수"""
    print(f"[BACS 헬스체크] 장비 목록 로딩: {devices_path}")

    # 장비 목록 로딩
    devices = load_devices(devices_path)
    print(f"  → {len(devices)}대 장비 등록 확인")

    # 전체 장비 병렬 헬스체크
    print(f"  → UDP 헬스체크 시작 (병렬, 포트 7788, 타임아웃 5초)")
    results = await run_all(devices)

    # 결과 출력
    _print_results(results, debug=debug)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BACS UDP 헬스체크")
    parser.add_argument(
        "--devices",
        type=Path,
        default=DEFAULT_DEVICES_PATH,
        help=f"devices.json 경로 (기본값: {DEFAULT_DEVICES_PATH})",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="송수신 패킷 hex 덤프 출력",
    )
    args = parser.parse_args()

    asyncio.run(main(args.devices, debug=args.debug))
