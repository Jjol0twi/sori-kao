"""디자인 시스템: 라이트/다크 팔레트와 타이포 토큰.

설정 화면 없이 시스템 외관(라이트/다크)에 자동으로 반응한다. macOS는
`AppleInterfaceStyle`로 다크 모드를 감지하고, 그 외 플랫폼은 라이트로 둔다.
색·폰트를 토큰으로 모아 GUI 전체가 한 곳에서 일관되게 스타일을 가져간다.
"""

import subprocess
import sys
from dataclasses import dataclass

# 색 토큰 — 역할 기반(컴포넌트가 아니라 의미로 명명)
PALETTES = {
    "light": {
        "bg": "#f5f5f7",          # 창/패널 배경
        "surface": "#ffffff",      # 카드(카모지) 표면
        "border": "#d0d0d5",       # 구분선/테두리
        "text": "#1c1c1e",         # 본문 텍스트
        "muted": "#6e6e73",        # 보조 텍스트
        "accent": "#0a84ff",       # 포커스/강조
        "danger": "#c0392b",       # 경고(빈 입력 등)
        "success": "#1a8f5a",      # 복사 완료 등
        "note": "#9a6a00",         # 낮은 신뢰도 안내
        "entry_bg": "#ffffff",
        "entry_fg": "#1c1c1e",
    },
    "dark": {
        "bg": "#1e1e1e",
        "surface": "#2c2c2e",
        "border": "#48484a",
        "text": "#f2f2f7",
        "muted": "#98989d",
        "accent": "#0a84ff",
        "danger": "#ff6b5e",
        "success": "#30d158",
        "note": "#ffd479",
        "entry_bg": "#2c2c2e",
        "entry_fg": "#f2f2f7",
    },
}

# 타이포 토큰 — (family, size[, style])
FONTS = {
    "hint": ("", 11),
    "entry": ("", 15),
    "section": ("", 12, "bold"),
    "category": ("", 13, "bold"),
    "reason": ("", 11),
    "secondary": ("", 11),
    "small": ("", 10),
    "empty": ("", 12),
}
KAOMOJI_FONTS = {"작음": ("", 16), "보통": ("", 24), "큼": ("", 34)}


def detect_mode() -> str:
    """현재 시스템 외관을 'dark' 또는 'light'로 반환한다."""
    if sys.platform == "darwin":
        try:
            out = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=1,
            )
            if out.returncode == 0 and "Dark" in out.stdout:
                return "dark"
        except Exception:
            pass
    return "light"


@dataclass
class Theme:
    """현재 모드에 맞는 색/폰트 토큰을 제공한다."""

    mode: str

    def c(self, token: str) -> str:
        """색 토큰 값."""
        return PALETTES[self.mode][token]

    def font(self, name: str):
        """폰트 토큰 값."""
        return FONTS[name]

    def kaomoji_font(self, size: str):
        """카모지 크기별 폰트."""
        return KAOMOJI_FONTS[size]
