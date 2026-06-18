"""입력에서 14차원 음운 특징 벡터를 뽑는다(build-prompt §6, design.md §5).

인덱스 순서는 :data:`FEATURE_NAMES`로 고정되며 `category_weights.json`의
`_meta.feature_order`와 1:1로 일치해야 한다. 모든 값은 [0, 1]로 정규화한다.

이 단계는 단어 뜻을 판단하지 않고, 입력의 소리 인상과 표기 리듬만 숫자로 낮춘다.
"""

import numpy as np

from text_preprocessor import PreprocessResult, preprocess

# 문서·가중치 JSON·설명 문장이 같은 축을 바라보도록 특징 순서를 고정한다.
FEATURE_NAMES = [
    "bright_vowel_ratio",        # 0
    "dark_vowel_ratio",          # 1
    "neutral_vowel_ratio",       # 2
    "tense_consonant_ratio",     # 3
    "aspirated_consonant_ratio", # 4
    "nasal_liquid_ratio",        # 5
    "final_consonant_density",   # 6
    "final_ng_ratio",            # 7
    "final_s_ratio",             # 8
    "syllable_repetition",       # 9
    "char_repetition",           # 10
    "exclaim_energy",            # 11
    "question_energy",           # 12
    "ellipsis_energy",           # 13
]
FEATURE_DIM = len(FEATURE_NAMES)

# 문헌의 음운 상징 논의를 구현 가능한 밝음/어두움/중립 축으로 단순화한다.
BRIGHT_VOWELS = set("ㅏㅐㅑㅒㅗㅘㅙㅚㅛ")
DARK_VOWELS = set("ㅓㅔㅕㅖㅜㅝㅞㅟㅠ")
NEUTRAL_VOWELS = set("ㅡㅢㅣ")

# 자음도 의미가 아니라 발음 인상으로만 본다. 초성 ㅇ은 소리값이 없어 세지 않는다.
TENSE_CONSONANTS = set("ㄲㄸㅃㅆㅉ")
ASPIRATED_CONSONANTS = set("ㅋㅌㅍㅊ")
NASAL_LIQUID_CONSONANTS = set("ㄴㅁㄹ")

S_FINALS = {"ㅅ", "ㅆ"}


def _syllable_repetition(chars) -> float:
    """길이 1~3의 인접 블록이 곧바로 반복되는 음절 비율."""
    n = len(chars)
    if n == 0:
        return 0.0
    marked = [False] * n
    for block in (1, 2, 3):
        i = 0
        while i + 2 * block <= n:
            if chars[i:i + block] == chars[i + block:i + 2 * block]:
                for j in range(i, i + 2 * block):
                    marked[j] = True
                i += block
            else:
                i += 1
    return sum(marked) / n


ELLIPSIS_CHARS = {".", "…"}


def _char_repetition(text: str) -> float:
    """같은 문자가 3회 이상 연속된 비율(자모·부호 포함, 말줄임표 제외)."""
    chars = [ch for ch in text if ch not in ELLIPSIS_CHARS]
    total = len(chars)
    if total == 0:
        return 0.0
    repeated = 0
    i = 0
    while i < total:
        j = i
        while j < total and chars[j] == chars[i]:
            j += 1
        if j - i >= 3:
            repeated += j - i
        i = j
    return repeated / total


def extract_features(result: PreprocessResult) -> np.ndarray:
    """전처리된 재료를 점수 모델이 읽을 수 있는 고정 길이 벡터로 바꾼다."""
    n = result.n
    vec = np.zeros(FEATURE_DIM, dtype=float)

    if n > 0:
        # 완성형 음절이 있을 때만 음운 비율을 채워, ㅋㅋ/ㅠㅠ가 가짜 모음 점수를 만들지 않게 한다.
        cho = [s.cho for s in result.syllables]
        jung = [s.jung for s in result.syllables]
        jong = [s.jong for s in result.syllables]

        vec[0] = sum(v in BRIGHT_VOWELS for v in jung) / n
        vec[1] = sum(v in DARK_VOWELS for v in jung) / n
        vec[2] = sum(v in NEUTRAL_VOWELS for v in jung) / n
        vec[3] = sum(c in TENSE_CONSONANTS for c in cho) / n
        vec[4] = sum(c in ASPIRATED_CONSONANTS for c in cho) / n
        vec[5] = sum(c in NASAL_LIQUID_CONSONANTS for c in cho) / n
        vec[6] = sum(j != "" for j in jong) / n
        vec[7] = sum(j == "ㅇ" for j in jong) / n
        vec[8] = sum(j in S_FINALS for j in jong) / n

    # 반복과 문장부호는 감정 자체가 아니라 강도·리듬·머뭇거림의 흔적으로만 쓴다.
    vec[9] = _syllable_repetition(result.syllable_chars)
    vec[10] = _char_repetition(result.repetition_chars)
    vec[11] = min(result.exclaim_count, 3) / 3
    vec[12] = min(result.question_count, 3) / 3
    vec[13] = min(result.ellipsis_count, 3) / 3
    return vec


def extract_features_from_text(text: str) -> np.ndarray:
    """문자열에서 곧바로 특징 벡터를 만든다(전처리 포함)."""
    return extract_features(preprocess(text))
