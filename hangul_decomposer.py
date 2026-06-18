"""한글 완성형 음절을 초성·중성·종성으로 분해한다.

design.md §4의 유니코드 계산 방식을 그대로 따른다.
완성형(`가`~`힣`)만 분해 대상이며, 그 외 문자는 None을 돌려준다.

이 모듈의 의도는 입력을 감정으로 해석하기 전, 한글을 계산 가능한 가장 작은
음운 단위로만 낮추는 것이다. 여기서는 의미나 카테고리를 붙이지 않는다.
"""

from collections import namedtuple

# Unicode 한글 조합표를 그대로 코드에 고정해 이후 단계가 같은 기준으로 음운을 읽게 한다.
# 초성 19, 중성 21, 종성 28(인덱스 0 = 받침 없음)
CHOSEONG = [
    "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
]
JUNGSEONG = [
    "ㅏ", "ㅐ", "ㅑ", "ㅒ", "ㅓ", "ㅔ", "ㅕ", "ㅖ", "ㅗ", "ㅘ",
    "ㅙ", "ㅚ", "ㅛ", "ㅜ", "ㅝ", "ㅞ", "ㅟ", "ㅠ", "ㅡ", "ㅢ", "ㅣ",
]
JONGSEONG = [
    "", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ",
    "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ",
]

HANGUL_BASE = 0xAC00  # '가'
HANGUL_END = 0xD7A3   # '힣'

# 초성·중성·종성 문자(종성은 받침 없을 때 빈 문자열)
Syllable = namedtuple("Syllable", ["cho", "jung", "jong"])


def is_hangul_syllable(ch: str) -> bool:
    """문자가 완성형 한글 음절(`가`~`힣`)인지 여부."""
    return len(ch) == 1 and HANGUL_BASE <= ord(ch) <= HANGUL_END


def decompose_syllable(ch: str):
    """완성형 음절 한 글자를 :class:`Syllable`로 분해한다.

    완성형이 아니면 ``None``을 반환한다. 받침이 없으면 ``jong``은 빈 문자열이다.
    """
    if not is_hangul_syllable(ch):
        return None
    s = ord(ch) - HANGUL_BASE
    cho = s // (21 * 28)
    jung = (s % (21 * 28)) // 28
    jong = s % 28
    return Syllable(CHOSEONG[cho], JUNGSEONG[jung], JONGSEONG[jong])


def decompose_text(text: str):
    """문자열에서 완성형 음절만 골라 :class:`Syllable` 리스트로 분해한다.

    완성형이 아닌 문자(자모·문장부호·영문·숫자·이모지)는 건너뛴다.
    """
    result = []
    for ch in text:
        syllable = decompose_syllable(ch)
        if syllable is not None:
            result.append(syllable)
    return result
