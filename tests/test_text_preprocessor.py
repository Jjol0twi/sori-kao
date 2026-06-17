"""text_preprocessor 단위 테스트(문자 분류·말줄임표 카운트)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_preprocessor import is_compat_jamo, preprocess


def test_standalone_jamo_excluded_from_syllables():
    result = preprocess("아ㅋ")
    assert result.n == 1                  # 완성형 '아'만 N에 포함
    assert result.jamo == ["ㅋ"]          # 단독 자모는 jamo로만
    assert is_compat_jamo("ㅋ") and not is_compat_jamo("아")


def test_emoji_letters_digits_ignored():
    result = preprocess("a1🔥")
    assert result.n == 0
    assert result.jamo == []
    assert result.syllables == []


def test_ellipsis_dots_and_unicode_equivalent():
    # '...'(마침표 3개)와 '…'가 각각 말줄임표 1건으로 동일 집계
    assert preprocess("아...").ellipsis_count == 1
    assert preprocess("아…").ellipsis_count == 1
    assert preprocess("아..").ellipsis_count == 0     # 2개는 아님
    assert preprocess("아......").ellipsis_count == 1  # 한 구간


def test_punctuation_counts():
    result = preprocess("뭐야?? 진짜!!!")
    assert result.exclaim_count == 3
    assert result.question_count == 2


def test_syllable_chars_preserved_in_order():
    result = preprocess("두근 두근")
    assert result.syllable_chars == ["두", "근", "두", "근"]
    assert result.n == 4


def test_empty_input():
    result = preprocess("   ")
    assert result.n == 0
    assert result.jamo == []
