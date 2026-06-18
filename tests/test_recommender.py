"""recommender 단위 테스트(결정성·크기 선택·동점/저신뢰 구성)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from recommender import SIZES, KaomojiRecommender
from scoring_model import ScoringModel


@pytest.fixture(scope="module")
def rec():
    return KaomojiRecommender()


@pytest.fixture(scope="module")
def model():
    return ScoringModel()


def test_select_by_size_returns_all_sizes(rec):
    selected = rec.select_by_size("응원")
    assert set(selected) == set(SIZES)
    # 카탈로그 등록 순서상 각 크기 첫 항목
    assert selected["작음"] == "٩( 'ω' )و"
    assert selected["보통"] == "(ง •̀ω•́)ง"
    assert selected["큼"] == "ᕦ(ò_óˇ)ᕤ"


def test_selection_is_deterministic(rec, model):
    result = model.score("아싸아싸!!")
    first = rec.recommend(result).primary_kaomoji
    second = rec.recommend(result).primary_kaomoji
    assert first == second  # 무작위 금지 → 동일 입력 동일 출력


def test_missing_size_falls_back(rec):
    # 특정 크기가 없으면 인접 크기로 대체(빈 값 없음)
    rec.catalog["테스트"] = [{"text": "(test)", "size": "보통"}]
    selected = rec.select_by_size("테스트")
    assert all(selected[s] for s in SIZES)
    assert selected["작음"] == "(test)"
    del rec.catalog["테스트"]


def test_low_confidence_trims_secondary(rec, model):
    result = model.score("아")  # 짧은 입력 → low
    assert result.confidence == "low"
    rec_out = rec.recommend(result)
    assert len(rec_out.secondary_categories) <= 1


def test_tie_produces_two_columns(rec, model):
    result = model.score("ㄷㄷ")  # 당황·긴장이 같은 자모 보조 점수로 동점
    rec_out = rec.recommend(result)
    assert len(rec_out.tie) >= 2
    assert rec_out.primary_category == result.tie_categories[0]
