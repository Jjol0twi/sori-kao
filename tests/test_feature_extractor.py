"""feature_extractor 단위 테스트."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feature_extractor import (
    FEATURE_DIM,
    FEATURE_NAMES,
    extract_features_from_text,
)


def _feat(text, name):
    return extract_features_from_text(text)[FEATURE_NAMES.index(name)]


def test_vector_dimension():
    assert FEATURE_DIM == 14
    assert len(FEATURE_NAMES) == 14
    assert extract_features_from_text("아무거나").shape == (14,)


def test_all_features_in_unit_range():
    for text in ["아싸아싸!!", "으으... 힘들다", "ㅋㅋㅋ 뭐야",
                 "값값값값값값", "", "lol123🔥", "?????"]:
        vec = extract_features_from_text(text)
        assert (vec >= 0).all() and (vec <= 1).all(), text


def test_empty_input_is_all_zero():
    vec = extract_features_from_text("")
    assert (vec == 0).all()


def test_bright_vowel_and_repetition():
    # 아싸아싸: 모두 밝은 모음 ㅏ, 2음절 블록이 반복
    assert _feat("아싸아싸", "bright_vowel_ratio") == 1.0
    assert _feat("아싸아싸", "syllable_repetition") == 1.0


def test_dark_vowel():
    # 우물쭈물류: 어두운 모음 비율이 0보다 큼
    assert _feat("우주", "dark_vowel_ratio") > 0


def test_final_consonant_features():
    # 값 = 겹받침 ㅄ → density 집계, ng/s 단일 종성에는 안 들어감
    assert _feat("값", "final_consonant_density") == 1.0
    assert _feat("값", "final_s_ratio") == 0.0
    # 강 = 종성 ㅇ
    assert _feat("강", "final_ng_ratio") == 1.0
    # 앗 = 종성 ㅅ
    assert _feat("앗", "final_s_ratio") == 1.0


def test_char_repetition_does_not_turn_jamo_only_input_into_generic_repetition():
    # 자모만 반복된 입력은 자모 보조 신호에서 다루고, 일반 반복 점수에는 넣지 않는다.
    assert _feat("ㅋㅋㅋ", "char_repetition") == 0.0
    assert _feat("ㅠㅠㅠ", "char_repetition") == 0.0
    assert _feat("!!!", "char_repetition") == 0.0
    assert _feat("아!!!", "char_repetition") == 0.75


def test_punctuation_energy_split_and_saturation():
    assert _feat("!!!", "exclaim_energy") == 1.0      # min(3,3)/3
    assert _feat("?", "question_energy") == 1.0 / 3
    assert _feat("좋아...", "ellipsis_energy") == 1.0 / 3
    # 부호 종류가 분리되어 서로 영향 없음
    assert _feat("!!!", "question_energy") == 0.0


def test_ellipsis_not_counted_as_generic_char_repetition():
    # 말줄임표는 ellipsis_energy 전용 신호이며, 일반 반복 점수를 올리지 않는다.
    assert _feat("...", "char_repetition") == 0.0
    assert _feat("…", "char_repetition") == 0.0
    assert _feat("아!!!", "char_repetition") == 0.75


def test_long_input_stays_normalized():
    vec = extract_features_from_text("아" * 200 + "!" * 50)
    assert (vec <= 1).all()


def test_ssang_s_final_counts():
    # 단일 종성 ㅆ도 final_s_ratio에 포함된다(났 = ㄴ/ㅏ/ㅆ)
    assert _feat("났", "final_s_ratio") == 1.0


def test_consonant_class_values():
    assert _feat("까", "tense_consonant_ratio") == 1.0        # ㄲ 된소리
    assert _feat("차", "aspirated_consonant_ratio") == 1.0    # ㅊ 거센소리
    assert _feat("나", "nasal_liquid_ratio") == 1.0           # ㄴ 비음
    assert _feat("라", "nasal_liquid_ratio") == 1.0           # ㄹ 유음


def test_h_initial_excluded_from_consonant_classes():
    # ㅎ은 어느 자음 비율에도 들어가지 않는다
    assert _feat("하", "tense_consonant_ratio") == 0.0
    assert _feat("하", "aspirated_consonant_ratio") == 0.0
    assert _feat("하", "nasal_liquid_ratio") == 0.0


def test_initial_ieung_excluded_from_nasal_liquid_ratio():
    # 초성 ㅇ은 소리값이 없으므로 비음·유음 비율에 넣지 않는다
    assert _feat("아", "nasal_liquid_ratio") == 0.0


def test_neutral_vowel_value():
    assert _feat("의", "neutral_vowel_ratio") == 1.0          # ㅢ 중성
