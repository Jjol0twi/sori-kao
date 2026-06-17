"""점수 결과를 카모지 추천으로 바꾼다(build-prompt §11). 선택은 결정적이다.

1위 카테고리에서 작음/보통/큼 각 1개를 카탈로그 등록 순서상 첫 항목으로 고른다.
무작위를 쓰지 않아 같은 입력은 항상 같은 카모지를 보여준다.
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
    """`kaomoji_catalog.json`에서 카테고리별 카모지를 결정적으로 고른다."""

    def __init__(self, catalog_path: str = _DEFAULT_CATALOG):
        with open(catalog_path, encoding="utf-8") as f:
            data = json.load(f)
        self.catalog = {k: v for k, v in data.items() if k != "_meta"}

    def select_by_size(self, category: str) -> dict:
        """카테고리에서 작음/보통/큼 카모지를 1개씩 고른다(없으면 인접 크기로 대체)."""
        entries = self.catalog.get(category, [])
        first_by_size = {}
        for entry in entries:
            first_by_size.setdefault(entry["size"], entry["text"])

        fallback = next(
            (first_by_size[s] for s in SIZES if s in first_by_size), None
        )
        return {size: first_by_size.get(size, fallback) for size in SIZES}

    def recommend(self, score_result) -> Recommendation:
        """:class:`ScoreResult`에서 추천 카모지 구조를 만든다."""
        tie_categories = score_result.tie_categories
        primary = tie_categories[0]
        tie = [(c, self.select_by_size(c)) for c in tie_categories]
        secondary = [c for c, _ in score_result.top3 if c not in tie_categories]
        # 신뢰도가 낮은(짧거나 모호한) 입력은 과도한 확신을 피해 후보를 1~2개로 줄인다
        if score_result.confidence == "low":
            secondary = secondary[:1]
        return Recommendation(
            primary_category=primary,
            primary_kaomoji=self.select_by_size(primary),
            tie=tie,
            secondary_categories=secondary,
        )
