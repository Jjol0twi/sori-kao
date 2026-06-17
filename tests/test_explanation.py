"""explanation 단위 테스트(이유 2개 보장·보조 신호·저신뢰 완화)."""

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
    # 완료 기준: 추천 이유 2개 이상(신호가 적은 입력 포함)
    for text in ["아싸아싸!!", "아", "으으... 힘들다", "음", ""]:
        explanation = build_explanation(model.score(text))
        assert len(explanation.reasons) >= 2, text


def test_auxiliary_signal_is_marked(model):
    # 키워드 보조가 1위에 기여하면 '보조 신호' 문장이 포함된다
    explanation = build_explanation(model.score("고마워요ㅎㅎ"))
    assert any("보조 신호" in r for r in explanation.reasons)


def test_conventional_pattern_signal_is_marked_separately(model):
    # 하품 같은 관습 표현은 키워드·자모가 아니라 관습 패턴 보조 신호로 설명한다
    explanation = build_explanation(model.score("하암"))
    assert any("관습 표현" in r for r in explanation.reasons)
    assert any("구분하기 어려워" in r for r in explanation.reasons)
    assert all("키워드·자모" not in r for r in explanation.reasons)


def test_low_confidence_note(model):
    explanation = build_explanation(model.score("아"))
    assert explanation.confidence == "low"
    assert explanation.note
    assert "후보" in explanation.note


def test_high_confidence_has_no_note(model):
    explanation = build_explanation(model.score("빠샤 집중하자"))
    assert explanation.confidence == "high"
    assert explanation.note == ""


def test_reasons_come_from_real_contributions(model):
    # 실제 점수에 기여한 특징만 이유로 쓰인다(빈 입력은 fallback 문장)
    explanation = build_explanation(model.score("아싸아싸!!"))
    assert explanation.category == "응원"
    assert all(isinstance(r, str) and r for r in explanation.reasons)
