#!/usr/bin/env bash
# macOS 단독 실행 앱(.app) 빌드 스크립트.
#
# 사용: 프로젝트 루트에서  bash scripts/build_macos_app.sh
# 결과: dist/sori-kao.app  (더블클릭 또는  open dist/sori-kao.app)
#
# 터미널 스크립트가 아니라 정식 .app 번들로 실행되면 macOS가 표준 앱으로
# 인식하므로, 편집 메뉴/클립보드 단축키(Cmd+C·V·X·A)가 더 안정적으로 동작한다.
# Tk 8.6이 포함된 Python(예: uv python 3.13)에서 빌드해야 한다.
set -euo pipefail

cd "$(dirname "$0")/.."

uv run --with pyinstaller pyinstaller \
  --noconfirm \
  --windowed \
  --name sori-kao \
  --add-data "data:data" \
  app.py

echo
echo "빌드 완료: dist/sori-kao.app"
echo "실행:      open dist/sori-kao.app"
