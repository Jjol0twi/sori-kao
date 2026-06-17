"""scoring_model 단위 테스트(점수 계산 메커니즘 검증)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from scoring_model import CATEGORIES, ScoringModel


@pytest.fixture(scope="module")
def model():
    return ScoringModel()


def test_top3_length_and_descending(model):
    result = model.score("아싸아싸!!")
    assert len(result.top3) == 3
    scores = [s for _, s in result.ranked]
    assert scores == sorted(scores, reverse=True)
    assert len(result.ranked) == len(CATEGORIES)


def test_zero_score_input_ranked_order_and_no_fake_tie(model):
    # 모든 점수 0인 퇴화 입력: ranked는 CATEGORIES 순서, 가짜 동점은 만들지 않음
    result = model.score("")
    assert [c for c, _ in result.ranked] == CATEGORIES
    assert result.tie_categories == ["응원"]  # top_score<=0이면 동점으로 보지 않음
    assert result.confidence == "low"


def test_partial_tie_follows_category_order(model):
    # 일부 카테고리만 양수 점수로 1위 동점일 때 §3 순서를 따른다
    result = model.score("죄송")  # 기쁨·감사가 1.0으로 동점
    assert len(result.tie_categories) >= 2
    # 동점 그룹이 CATEGORIES 상대 순서를 유지
    indexed = [CATEGORIES.index(c) for c in result.tie_categories]
    assert indexed == sorted(indexed)
    # ranked의 동점 블록도 같은 순서
    top = result.ranked[0][1]
    tied_in_ranked = [c for c, s in result.ranked if s == top]
    assert tied_in_ranked == result.tie_categories


def test_confidence_low_for_short_input(model):
    assert model.score("아").confidence == "low"


def test_auxiliary_bonus_capped(model):
    # 감사+고마 = 0.4+0.4=0.8 → 상한 0.5로 잘림
    result = model.score("감사 고마워")
    assert result.auxiliary["감사"] == pytest.approx(0.5)


def test_contributions_are_positive_only(model):
    result = model.score("아싸아싸!!")
    assert result.contributions  # 비어 있지 않음
    assert all(val > 0 for _, val in result.contributions)


def test_keyword_routes_to_expected_category(model):
    # 보조 키워드가 해당 카테고리 점수를 끌어올린다
    assert model.score("고마워요ㅎㅎ").top_category == "감사"


def test_tense_and_punctuation_drive_focus_anger(model):
    # 빡세다 진짜! → 집중/분노/긴장 계열이 상위
    top3 = {c for c, _ in model.score("빡세다 진짜!").top3}
    assert top3 & {"집중", "분노", "긴장"}


def test_invalid_feature_order_raises(tmp_path):
    import json
    bad = {
        "_meta": {
            "feature_order": ["wrong"],
            "auxiliary_bonus_cap": 0.5,
            "confidence": {"min_syllables": 2, "score_gap_ratio": 0.15},
        },
        "categories": {}, "auxiliary_keywords": {},
    }
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError):
        ScoringModel(str(path))
