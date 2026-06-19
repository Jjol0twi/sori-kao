"""설계서 §14 기반 회귀 테스트.

성공 기준(design.md §14): 기대 음운 인상 축 중 하나라도 Top-3에 들면 성공.
음운 상징 매핑은 경향이라 100%를 요구하지 않고 "대체로"(>=70%) 충족을 본다.
일부는 가중치 조정에 쓰지 않은 hold-out으로 분리한다.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from scoring_model import CATEGORIES, ScoringModel

# 가중치 조정에 참고한 사례
TUNING_CASES = [
    ("아싸아싸!!", {"밝음·가벼움", "반복·리듬", "강함·격렬함"}),
    ("아기", {"밝음·가벼움", "작음·섬세함"}),
    ("야야", {"밝음·가벼움", "작음·섬세함", "반복·리듬"}),
    ("으으...", {"어두움·무거움", "지속·여운", "반복·리듬"}),
    ("빠샤!", {"강함·격렬함", "밝음·가벼움"}),
    ("구르구르", {"반복·리듬", "부드러움·흐름"}),
    ("앗!", {"막힘·단절감", "밝음·가벼움", "강함·격렬함"}),
    ("쿵쿵", {"큼·둔중함", "어두움·무거움", "반복·리듬", "막힘·단절감"}),
    ("ㅠㅠㅠ", {"지속·여운", "반복·리듬"}),
    ("사각사각", {"밝음·가벼움", "반복·리듬", "막힘·단절감"}),
]

# hold-out — 가중치 조정에 사용하지 않은 사례(자기충족 평가 방지, design §14)
HOLDOUT_CASES = [
    ("하암", {"밝음·가벼움"}),
    ("추카", {"강함·격렬함", "밝음·가벼움"}),
    ("축하", {"강함·격렬함", "막힘·단절감", "어두움·무거움"}),
    ("우우...", {"어두움·무거움", "지속·여운", "반복·리듬"}),
    ("똑딱똑딱", {"강함·격렬함", "막힘·단절감", "반복·리듬"}),
    ("나른나른", {"부드러움·흐름", "반복·리듬"}),
    ("물렁물렁", {"부드러움·흐름", "반복·리듬", "큼·둔중함"}),
    ("살랑살랑", {"밝음·가벼움", "부드러움·흐름", "반복·리듬", "지속·여운"}),
    ("까칠까칠", {"강함·격렬함", "반복·리듬", "막힘·단절감"}),
    ("둥둥", {"큼·둔중함", "어두움·무거움", "반복·리듬", "지속·여운"}),
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
    assert "반복·리듬" in _top3(model, "아싸아싸!!")
    assert model.score("ㅋㅋㅋ").top_category == "반복·리듬"
    assert {"반복·리듬", "지속·여운"}.issubset(_top3(model, "ㅠㅠㅠ"))
    assert model.score("하암").top_category == "밝음·가벼움"
    assert "강함·격렬함" in _top3(model, "빠샤!")


def test_no_emotion_keyword_shortcut(model):
    # 의미 단어가 감정 카테고리로 우회하지 않고, 새 음운 인상 축만 반환된다.
    for text in ["고마워요", "미안해 정말", "화나", "힘들다"]:
        assert _top3(model, text) <= set(CATEGORIES)
        assert not model.score(text).auxiliary
    assert model.score("고마워요ㅎㅎ").auxiliary == {"반복·리듬": 0.5}


def test_low_confidence_for_ambiguous(model):
    assert model.score("아").confidence == "low"
    assert model.score("음").confidence == "low"
    assert model.score("하암").confidence == "low"
