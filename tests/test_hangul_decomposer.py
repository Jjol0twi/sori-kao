"""hangul_decomposer 단위 테스트."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hangul_decomposer import (
    decompose_syllable,
    decompose_text,
    is_hangul_syllable,
)


def test_is_hangul_syllable():
    assert is_hangul_syllable("가")
    assert is_hangul_syllable("힣")
    assert not is_hangul_syllable("ㅋ")   # 호환 자모는 완성형이 아님
    assert not is_hangul_syllable("A")
    assert not is_hangul_syllable("!")
    assert not is_hangul_syllable("")     # 빈 문자열


def test_decompose_with_jong():
    # 값 = ㄱ + ㅏ + ㅄ(겹받침)
    assert decompose_syllable("값") == ("ㄱ", "ㅏ", "ㅄ")
    # 한 = ㅎ + ㅏ + ㄴ
    assert decompose_syllable("한") == ("ㅎ", "ㅏ", "ㄴ")


def test_decompose_without_jong():
    cho, jung, jong = decompose_syllable("아")
    assert (cho, jung) == ("ㅇ", "ㅏ")
    assert jong == ""  # 받침 없음은 빈 문자열


def test_decompose_boundaries():
    assert decompose_syllable("가") == ("ㄱ", "ㅏ", "")
    assert decompose_syllable("힣") == ("ㅎ", "ㅣ", "ㅎ")


def test_decompose_non_hangul_returns_none():
    assert decompose_syllable("A") is None
    assert decompose_syllable("ㅋ") is None
    assert decompose_syllable("1") is None


def test_decompose_text_filters_non_syllables():
    # 완성형만 남고 자모·부호는 제외
    syllables = decompose_text("아싸!! ㅋㅋ")
    assert len(syllables) == 2
    assert [s.cho for s in syllables] == ["ㅇ", "ㅆ"]


def test_decompose_text_empty():
    assert decompose_text("") == []
    assert decompose_text("lol123") == []
