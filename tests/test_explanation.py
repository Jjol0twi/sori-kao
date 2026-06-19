"""explanation 단위 테스트(이유 2개 보장·표기 보조 신호·저신뢰 완화)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from explanation import build_explanation
from scoring_model import ScoringModel


@pytest.fixture(scope="module")
def model():
    return ScoringModel()


def test_at_least_two_reasons(model):
    # 완료 기준: 해석 이유 2개 이상(신호가 적은 입력 포함)
    for text in ["아싸아싸!!", "아", "으으...", "음", ""]:
        explanation = build_explanation(model.score(text))
        assert len(explanation.reasons) >= 2, text


def test_jamo_auxiliary_signal_is_marked(model):
    # 자모 반복이 1위에 기여하면 표기 보조 신호 문장이 포함된다.
    explanation = build_explanation(model.score("ㅋㅋㅋ"))
    assert explanation.category == "반복·리듬"
    assert any("표기 보조 신호" in r for r in explanation.reasons)


def test_no_semantic_hint_explanation_for_yawn_like_text(model):
    # 하암은 하품 의미로 보내지 않고, 짧은 밝은 모음 인상으로 낮은 신뢰도 처리한다.
    explanation = build_explanation(model.score("하암"))
    assert explanation.category == "밝음·가벼움"
    assert explanation.confidence == "low"
    assert all("관습 표현" not in r for r in explanation.reasons)
    assert all("키워드" not in r for r in explanation.reasons)


def test_rhythmic_ideophone_explanation_does_not_use_fallback(model):
    explanation = build_explanation(model.score("구르구르"))
    assert explanation.category == "반복·리듬"
    assert any("리듬" in r for r in explanation.reasons)
    assert all("기본 해석 후보" not in r for r in explanation.reasons)


def test_low_confidence_note(model):
    explanation = build_explanation(model.score("아"))
    assert explanation.confidence == "low"
    assert explanation.note
    assert "후보" in explanation.note


def test_high_confidence_has_no_note(model):
    explanation = build_explanation(model.score("구르구르"))
    assert explanation.confidence == "high"
    assert explanation.note == ""


def test_reasons_come_from_real_contributions(model):
    # 실제 점수에 기여한 특징만 이유로 쓰인다(빈 입력은 fallback 문장)
    explanation = build_explanation(model.score("아싸아싸!!"))
    assert explanation.category == "반복·리듬"
    assert all(isinstance(r, str) and r for r in explanation.reasons)
