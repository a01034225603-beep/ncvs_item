#!/usr/bin/env bash
# ============================================================
# build-windows-package.sh
# Windows Portable 패키지 빌드 스크립트 (macOS/Linux 개발 머신에서 실행)
#
# 전제:
#   - 인터넷 가능한 개발 머신에서 1회 실행
#   - Python 3.12, Node.js 20, curl, zip 필요
#
# 결과:
#   dist/ncvs-package-YYYYMMDD.zip  ← Windows PC에 USB로 전달
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DATE_TAG=$(date +%Y%m%d)
OUT_DIR="$ROOT_DIR/dist/ncvs-package"
ZIP_NAME="ncvs-package-$DATE_TAG.zip"

PYTHON_VERSION="3.12.10"
NODE_VERSION="20.19.2"

echo "============================================"
echo " NCVS Windows Portable 패키지 빌드"
echo " 출력: dist/$ZIP_NAME"
echo "============================================"

# ── 기존 빌드 정리 ──────────────────────────────────────────
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"/{python,node,backend,frontend,data,scripts}

# ── Step 1: Next.js standalone 빌드 ─────────────────────────
echo ""
echo "[Step 1] Next.js standalone 빌드..."
cd "$ROOT_DIR/frontend"
BACKEND_URL="http://localhost:8000" npm run build

# standalone 빌드 결과 복사
cp -r .next/standalone/. "$OUT_DIR/frontend/"
cp -r public "$OUT_DIR/frontend/public"
# standalone은 .next/static을 별도로 복사해야 함
mkdir -p "$OUT_DIR/frontend/.next"
cp -r .next/static "$OUT_DIR/frontend/.next/static"
echo "[Step 1] 완료"

# ── Step 2: Python 3.12 Windows embeddable 다운로드 ─────────
echo ""
echo "[Step 2] Python $PYTHON_VERSION Windows embeddable 다운로드..."
PYTHON_ZIP="python-$PYTHON_VERSION-embed-amd64.zip"
PYTHON_URL="https://www.python.org/ftp/python/$PYTHON_VERSION/$PYTHON_ZIP"
cd "$ROOT_DIR/dist"

if [ ! -f "$PYTHON_ZIP" ]; then
    curl -L -o "$PYTHON_ZIP" "$PYTHON_URL"
fi
unzip -q -o "$PYTHON_ZIP" -d "$OUT_DIR/python/"

# embeddable은 site-packages 비활성화되어 있음 → python312._pth 에서 활성화
PTH_FILE="$OUT_DIR/python/python312._pth"
if [ -f "$PTH_FILE" ]; then
    # import site 주석 해제
    sed -i.bak 's/#import site/import site/' "$PTH_FILE"
    rm -f "${PTH_FILE}.bak"
fi
echo "[Step 2] 완료"

# ── Step 3: pip 설치 (get-pip.py) ───────────────────────────
echo ""
echo "[Step 3] pip 설치..."
GET_PIP="$ROOT_DIR/dist/get-pip.py"
if [ ! -f "$GET_PIP" ]; then
    curl -sS https://bootstrap.pypa.io/get-pip.py -o "$GET_PIP"
fi
"$OUT_DIR/python/python.exe" "$GET_PIP" --no-warn-script-location 2>/dev/null || true
echo "[Step 3] 완료"

# ── Step 4: Windows용 wheel 사전 다운로드 → 설치 ────────────
echo ""
echo "[Step 4] Windows pip wheel 다운로드 및 설치..."
WHEELS_DIR="$ROOT_DIR/dist/wheels"
mkdir -p "$WHEELS_DIR"

# macOS에서 Windows AMD64 바이너리 wheel 다운로드
pip download \
    --platform win_amd64 \
    --python-version 312 \
    --only-binary :all: \
    -r "$SCRIPT_DIR/requirements-windows.txt" \
    -d "$WHEELS_DIR/" \
    --quiet

echo "[Step 4] 완료 ($(ls "$WHEELS_DIR" | wc -l | tr -d ' ')개 wheel)"

# ── Step 5: Node.js 20 Windows portable 다운로드 ────────────
echo ""
echo "[Step 5] Node.js $NODE_VERSION Windows portable 다운로드..."
NODE_ZIP="node-v$NODE_VERSION-win-x64.zip"
NODE_URL="https://nodejs.org/dist/v$NODE_VERSION/$NODE_ZIP"
cd "$ROOT_DIR/dist"

if [ ! -f "$NODE_ZIP" ]; then
    curl -L -o "$NODE_ZIP" "$NODE_URL"
fi
# node.exe만 추출
unzip -q -o "$NODE_ZIP" "node-v$NODE_VERSION-win-x64/node.exe" -d "$ROOT_DIR/dist/node_tmp/"
cp "$ROOT_DIR/dist/node_tmp/node-v$NODE_VERSION-win-x64/node.exe" "$OUT_DIR/node/node.exe"
rm -rf "$ROOT_DIR/dist/node_tmp"
echo "[Step 5] 완료"

# ── Step 6: 백엔드 소스 복사 ────────────────────────────────
echo ""
echo "[Step 6] 백엔드 소스 복사..."
rsync -a \
    --exclude=__pycache__ \
    --exclude=.pytest_cache \
    --exclude=".env" \
    --exclude="*.pyc" \
    "$ROOT_DIR/backend/" "$OUT_DIR/backend/"

# 로컬용 .env 적용 (.env.local → .env)
cp "$ROOT_DIR/backend/.env.local" "$OUT_DIR/backend/.env"

# wheels 디렉터리도 포함 (install.bat에서 사용)
cp -r "$WHEELS_DIR" "$OUT_DIR/wheels"
echo "[Step 6] 완료"

# ── Step 7: 런처 배치 파일 복사 ─────────────────────────────
echo ""
echo "[Step 7] 런처 파일 복사..."
cp "$SCRIPT_DIR/windows/install.bat" "$OUT_DIR/"
cp "$SCRIPT_DIR/windows/start.bat"   "$OUT_DIR/"
cp "$SCRIPT_DIR/windows/stop.bat"    "$OUT_DIR/"
cp "$SCRIPT_DIR/windows/README.txt"  "$OUT_DIR/"
echo "[Step 7] 완료"

# ── Step 8: ZIP 압축 ─────────────────────────────────────────
echo ""
echo "[Step 8] ZIP 압축 중..."
cd "$ROOT_DIR/dist"
zip -r "$ZIP_NAME" "ncvs-package/" --quiet
echo "[Step 8] 완료: dist/$ZIP_NAME ($(du -sh "$ZIP_NAME" | cut -f1))"

echo ""
echo "============================================"
echo " 빌드 완료!"
echo " → dist/$ZIP_NAME 을 Windows PC로 전달하세요"
echo "============================================"
