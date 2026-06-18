"""점수 결과를 카모지 추천으로 바꾼다(build-prompt §11). 선택은 결정적이다.

1위 카테고리에서 작음/보통/큼 각 1개를 카탈로그 등록 순서상 첫 항목으로 고른다.
무작위를 쓰지 않아 같은 입력은 항상 같은 카모지를 보여준다.

이 단계는 점수를 다시 해석하지 않고, 이미 정해진 카테고리를 화면에 보여줄
표현물로만 바꾼다.
"""

import json
import os
from dataclasses import dataclass

SIZES = ["작음", "보통", "큼"]

_DEFAULT_CATALOG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "kaomoji_catalog.json"
)


@dataclass
class Recommendation:
    primary_category: str
    primary_kaomoji: dict             # {size: text}
    tie: list                         # [(category, {size: text}), ...] 동점 카테고리(순서 고정)
    secondary_categories: list        # Top-3 중 1위(동점 포함)를 뺀 나머지 카테고리명


class KaomojiRecommender:
    """점수 모델과 분리된 카모지 카탈로그를 결정적으로 조회한다."""

    def __init__(self, catalog_path: str = _DEFAULT_CATALOG):
        with open(catalog_path, encoding="utf-8") as f:
            data = json.load(f)
        self.catalog = {k: v for k, v in data.items() if k != "_meta"}

    def select_by_size(self, category: str) -> dict:
        """같은 카테고리 안에서 표현 크기만 달리해 사용자가 고를 여지를 남긴다."""
        entries = self.catalog.get(category, [])
        first_by_size = {}
        for entry in entries:
            first_by_size.setdefault(entry["size"], entry["text"])

        fallback = next(
            (first_by_size[s] for s in SIZES if s in first_by_size), None
        )
        return {size: first_by_size.get(size, fallback) for size in SIZES}

    def recommend(self, score_result) -> Recommendation:
        """점수 결과를 재현 가능한 추천 목록으로 고정한다."""
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
