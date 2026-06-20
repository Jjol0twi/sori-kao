"""음운 인상 결과에 선택적 카모지 표시물을 붙인다. 선택은 결정적이다.

1위 인상 축에서 작음/보통/큼 각 크기의 카탈로그 항목을 등록 순서대로 모두 모은다.
무작위를 쓰지 않아 같은 입력은 항상 같은 표시물(같은 순서)을 보여준다.

이 단계는 점수를 다시 해석하지 않고, 이미 정해진 인상 축을 화면에 보여줄
표현물로만 바꾼다. 카모지는 핵심 결과가 아니라 부가 표시물이다.
"""

import json
import os
import sys
from dataclasses import dataclass

SIZES = ["작음", "보통", "큼"]

# PyInstaller로 .app 번들이 되면 데이터가 sys._MEIPASS 아래에 풀린다(개발 모드는 파일 위치).
_DEFAULT_CATALOG = os.path.join(
    getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))),
    "data", "kaomoji_catalog.json",
)


@dataclass
class Recommendation:
    primary_category: str
    primary_kaomoji: dict             # {size: [text, ...]}
    tie: list                         # [(category, {size: [text, ...]}), ...] 동점 축(순서 고정)
    secondary_categories: list        # Top-3 중 1위(동점 포함)를 뺀 나머지 축명


class KaomojiRecommender:
    """해석 모델과 분리된 카모지 카탈로그를 결정적으로 조회한다."""

    def __init__(self, catalog_path: str = _DEFAULT_CATALOG):
        with open(catalog_path, encoding="utf-8") as f:
            data = json.load(f)
        self.catalog = {k: v for k, v in data.items() if k != "_meta"}

    def select_by_size(self, category: str) -> dict:
        """같은 인상 축의 카모지를 크기별로 모두 모아 여러 개를 보여줄 수 있게 한다."""
        by_size = {size: [] for size in SIZES}
        for entry in self.catalog.get(category, []):
            if entry["size"] in by_size:
                by_size[entry["size"]].append(entry["text"])

        # 비어 있는 크기는 다른 크기에서 하나 빌려와 빈 칸이 생기지 않게 한다(결정적).
        fallback = next((by_size[s][0] for s in SIZES if by_size[s]), None)
        if fallback:
            for size in SIZES:
                if not by_size[size]:
                    by_size[size] = [fallback]
        return by_size

    def recommend(self, score_result) -> Recommendation:
        """점수 결과를 재현 가능한 표시 목록으로 고정한다."""
        tie_categories = score_result.tie_categories
        primary = tie_categories[0]
        tie = [(c, self.select_by_size(c)) for c in tie_categories]
        secondary = [c for c, _ in score_result.top3 if c not in tie_categories]
        # 낮은 신뢰도 입력은 많이 보여주는 대신, 조심스러운 후보처럼 보이게 줄인다.
        if score_result.confidence == "low":
            secondary = secondary[:1]
        return Recommendation(
            primary_category=primary,
            primary_kaomoji=self.select_by_size(primary),
            tie=tie,
            secondary_categories=secondary,
        )
