"""scoring_model 단위 테스트(음운 인상 점수 계약 검증)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from scoring_model import CATEGORIES, ScoringModel


EXPECTED_CATEGORIES = [
    "밝음·가벼움",
    "어두움·무거움",
    "작음·섬세함",
    "큼·둔중함",
    "강함·격렬함",
    "부드러움·흐름",
    "반복·리듬",
    "지속·여운",
    "막힘·단절감",
]


@pytest.fixture(scope="module")
def model():
    return ScoringModel()


def test_category_contract_uses_phonetic_impression_axes():
    assert CATEGORIES == EXPECTED_CATEGORIES
    assert "변화·교체감" not in CATEGORIES  # MVP 미산출 확장 축


def test_top3_length_and_descending(model):
    result = model.score("아싸아싸!!")
    assert len(result.top3) == 3
    scores = [s for _, s in result.ranked]
    assert scores == sorted(scores, reverse=True)
    assert len(result.ranked) == len(CATEGORIES)


def test_zero_score_input_ranked_order_and_no_fake_tie(model):
    result = model.score("")
    assert [c for c, _ in result.ranked] == CATEGORIES
    assert result.tie_categories == ["밝음·가벼움"]
    assert result.confidence == "low"


def test_bright_repeated_expression_returns_impression_axes(model):
    result = model.score("아싸아싸!!")
    top3 = {c for c, _ in result.top3}
    assert {"밝음·가벼움", "반복·리듬", "강함·격렬함"} & top3
    assert "반복·리듬" in top3
    assert top3 <= set(EXPECTED_CATEGORIES)


def test_dark_lingering_expression_returns_dark_and_linger(model):
    top3 = {c for c, _ in model.score("우우...").top3}
    assert "어두움·무거움" in top3
    assert "지속·여운" in top3


def test_tense_aspirated_and_punctuation_drive_intensity(model):
    top3 = {c for c, _ in model.score("빠샤!").top3}
    assert "강함·격렬함" in top3
    assert "밝음·가벼움" in top3


def test_repeated_ideophone_returns_rhythm_without_emotion_category(model):
    result = model.score("구르구르")
    assert result.top_category == "반복·리듬"
    assert {c for c, _ in result.top3} <= set(EXPECTED_CATEGORIES)


def test_jamo_repetition_maps_to_notational_rhythm_and_low_confidence(model):
    laugh = model.score("ㅋㅋㅋ")
    cry = model.score("ㅠㅠㅠ")

    assert laugh.top_category == "반복·리듬"
    assert laugh.auxiliary_sources["반복·리듬"] == ["jamo"]
    assert laugh.confidence == "low"

    cry_top3 = {c for c, _ in cry.top3}
    assert "반복·리듬" in cry_top3
    assert "지속·여운" in cry_top3
    assert cry.confidence == "low"


def test_no_keyword_or_semantic_hint_layer(model):
    result = model.score("고마워요ㅎㅎ")
    assert not any(source.startswith("semantic:") for sources in result.auxiliary_sources.values() for source in sources)
    assert {c for c, _ in result.top3} <= set(EXPECTED_CATEGORIES)


def test_short_bright_expression_is_low_confidence_not_yawn_meaning(model):
    result = model.score("하암")
    assert result.top_category == "밝음·가벼움"
    assert result.confidence == "low"
    assert not result.auxiliary_sources


def test_close_top_scores_can_be_high_when_they_are_compound_impressions(model):
    # 불파 폐쇄음 받침(ㄱ) 의성어: 막힘·단절(종성) + 강함(된소리) + 반복이 함께 뜬다.
    # ('쿵쾅'은 종성이 ㅇ(공명)이라 막힘이 아니라 여운으로 가는 게 옳으므로 폐쇄 받침 예로 교체)
    result = model.score("똑딱똑딱")
    assert result.confidence == "high"
    assert {"강함·격렬함", "반복·리듬", "막힘·단절감"}.issubset(
        {category for category, _ in result.top3}
    )


def test_spelling_pronunciation_forms_can_differ_without_g2p(model):
    spelling = model.score("축하")
    pronunciation = model.score("추카")

    assert spelling.features.tolist() != pronunciation.features.tolist()
    assert spelling.top3 != pronunciation.top3


def test_contributions_are_positive_descending_and_match_formula(model):
    import numpy as np
    from feature_extractor import FEATURE_NAMES

    result = model.score("아싸아싸!!")
    assert result.contributions
    values = [v for _, v in result.contributions]
    assert values == sorted(values, reverse=True)
    assert all(val > 0 for _, val in result.contributions)

    top_idx = CATEGORIES.index(result.top_category)
    contrib = result.features * model.weights[top_idx]
    name, val = result.contributions[0]
    assert val == pytest.approx(contrib[FEATURE_NAMES.index(name)])
    assert val == pytest.approx(float(np.max(contrib)))
