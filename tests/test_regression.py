"""설계서 §14 테스트 입력 기반 회귀 테스트.

성공 기준(design.md §14): 기대 카테고리 중 하나라도 Top-3에 들면 성공.
음운-감정 매핑은 경향이라 100%를 요구하지 않고 "대체로"(>=70%) 충족을 본다.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from scoring_model import ScoringModel

# (입력, 기대 카테고리 집합) — design.md §14 초안
DESIGN_CASES = [
    ("아싸아싸!!", {"응원", "기쁨", "장난"}),
    ("ㅋㅋㅋㅋ 뭐야", {"장난", "기쁨", "당황"}),
    ("으으... 힘들다", {"피곤", "긴장"}),
    ("고마워요ㅎㅎ", {"감사", "기쁨"}),
    ("죄송합니다...", {"사과", "긴장"}),
    ("빡세다 진짜!", {"분노", "집중", "긴장"}),
    ("빠샤 집중하자", {"응원", "집중"}),
    ("헉 뭐야??", {"당황", "긴장"}),
    ("아... 망했다", {"긴장", "피곤", "당황"}),
    ("우와!!!", {"기쁨", "당황"}),
]


@pytest.fixture(scope="module")
def model():
    return ScoringModel()


def _top3(model, text):
    return {c for c, _ in model.score(text).top3}


def test_overall_top3_hit_rate(model):
    hits = sum(bool(_top3(model, t) & expected) for t, expected in DESIGN_CASES)
    rate = hits / len(DESIGN_CASES)
    assert rate >= 0.7, f"기대 카테고리 Top-3 적중률 {rate:.0%} (< 70%)"


def test_strong_cases_always_hold(model):
    # 음운/키워드 신호가 분명해 항상 성립해야 하는 사례
    assert "응원" in _top3(model, "아싸아싸!!")
    assert model.score("고마워요ㅎㅎ").top_category == "감사"
    assert _top3(model, "빡세다 진짜!") & {"분노", "집중", "긴장"}


def test_low_confidence_for_ambiguous(model):
    # 짧거나 한글이 부족한 입력은 낮은 신뢰도
    assert model.score("아").confidence == "low"
    assert model.score("음").confidence == "low"
