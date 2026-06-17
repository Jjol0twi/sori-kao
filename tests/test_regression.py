"""설계서 §14 기반 회귀 테스트.

성공 기준(design.md §14): 기대 카테고리 중 하나라도 Top-3에 들면 성공.
음운-감정 매핑은 경향이라 100%를 요구하지 않고 "대체로"(>=70%) 충족을 본다.
development-goal §14 요구에 맞춰 카테고리당 2개 이상, 총 20개 이상으로 확장하고,
일부는 가중치 조정에 쓰지 않은 hold-out으로 분리한다.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from scoring_model import CATEGORIES, ScoringModel

# design.md §14 초안 10개 — 가중치 조정에 참고한 사례
TUNING_CASES = [
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

# hold-out — 가중치 조정에 사용하지 않은 사례(자기충족 평가 방지, design §14)
HOLDOUT_CASES = [
    ("으악 짜증나", {"분노", "긴장"}),
    ("미안해 정말", {"사과", "긴장"}),
    ("고맙습니다", {"감사"}),
    ("파이팅!!", {"응원", "기쁨"}),
    ("하하하 웃겨", {"기쁨", "장난"}),
    ("집중하자", {"집중"}),
    ("꺄악 깜짝이야", {"당황", "긴장", "분노"}),
    ("빡치네 진짜", {"분노", "집중"}),
    ("졸려 죽겠다", {"피곤"}),
    ("두근두근거려", {"긴장", "피곤"}),
]

DESIGN_CASES = TUNING_CASES + HOLDOUT_CASES


@pytest.fixture(scope="module")
def model():
    return ScoringModel()


def _top3(model, text):
    return {c for c, _ in model.score(text).top3}


def _hit_rate(model, cases):
    hits = sum(bool(_top3(model, t) & expected) for t, expected in cases)
    return hits / len(cases)


def test_case_count_and_per_category_coverage():
    # development-goal §14: 총 20개 이상, 카테고리당 최소 2개
    assert len(DESIGN_CASES) >= 20
    for category in CATEGORIES:
        count = sum(category in expected for _, expected in DESIGN_CASES)
        assert count >= 2, f"{category} 기대 케이스 {count}개 (< 2)"


def test_overall_top3_hit_rate(model):
    rate = _hit_rate(model, DESIGN_CASES)
    assert rate >= 0.7, f"전체 Top-3 적중률 {rate:.0%} (< 70%)"


def test_holdout_hit_rate(model):
    # hold-out도 대체로 적중해야 한다(과적합 점검)
    rate = _hit_rate(model, HOLDOUT_CASES)
    assert rate >= 0.6, f"hold-out 적중률 {rate:.0%} (< 60%)"


def test_strong_cases_always_hold(model):
    assert "응원" in _top3(model, "아싸아싸!!")
    assert model.score("고마워요ㅎㅎ").top_category == "감사"
    assert _top3(model, "빡세다 진짜!") & {"분노", "집중", "긴장"}


def test_low_confidence_for_ambiguous(model):
    assert model.score("아").confidence == "low"
    assert model.score("음").confidence == "low"
