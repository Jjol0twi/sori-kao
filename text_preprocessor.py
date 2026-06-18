"""입력 문자열을 분석 단위로 분류한다(design.md §3 TextPreprocessor, build-prompt §5).

입력을 다음으로 나눈다.
- 완성형 음절: 초성·중성·종성으로 분해하고 ``N``에 포함한다.
- 호환 자모 단독(`ㅋ`,`ㅠ`): 음운 벡터에는 안 쓰고 자모 패턴/반복에만 기여한다.
- 문장부호(`!`,`?`,`…`/`...`): energy 특징으로만 쓴다.
- 영문·숫자·이모지: 무시한다.

이 단계의 의도는 의미 해석을 바로 시작하지 않고, 소리로 볼 부분과 채팅 관습으로
볼 부분을 먼저 분리하는 것이다.
"""

from dataclasses import dataclass, field

from hangul_decomposer import Syllable, decompose_syllable

# 한글 호환 자모 블록(U+3131 'ㄱ' ~ U+3163 'ㅣ'): 자판으로 입력되는 단독 자모
COMPAT_JAMO_START = 0x3131
COMPAT_JAMO_END = 0x3163


def is_compat_jamo(ch: str) -> bool:
    """문자가 단독 호환 자모(`ㄱ`~`ㅣ`)인지 여부."""
    return len(ch) == 1 and COMPAT_JAMO_START <= ord(ch) <= COMPAT_JAMO_END


@dataclass
class PreprocessResult:
    syllables: list = field(default_factory=list)        # 음운 벡터로 보낼 완성형 음절
    syllable_chars: list = field(default_factory=list)   # 음절 반복은 원문 글자 흐름에서 잡는다
    jamo: list = field(default_factory=list)             # ㅋㅋ/ㅠㅠ처럼 소리보다 관습에 가까운 신호
    repetition_chars: str = ""                           # 반복 리듬은 자모·부호까지 포함해 별도 축으로 본다
    exclaim_count: int = 0
    question_count: int = 0
    ellipsis_count: int = 0

    @property
    def n(self) -> int:
        """분석 대상 완성형 음절 수."""
        return len(self.syllables)


def _count_ellipsis(text: str) -> int:
    """말줄임표 개수: `…` 글자 수 + 마침표 3개 이상 연속 구간 수."""
    count = text.count("…")
    run = 0
    for ch in text:
        if ch == ".":
            run += 1
        else:
            if run >= 3:
                count += 1
            run = 0
    if run >= 3:
        count += 1
    return count


def preprocess(text: str) -> PreprocessResult:
    """뒤 단계가 같은 입력을 서로 다르게 읽지 않도록 분석 재료를 고정한다."""
    result = PreprocessResult()
    for ch in text:
        # 완성형 한글은 음운 분석으로 보내고, 단독 자모는 의미가 아니라 표현 관습으로 남긴다.
        syllable = decompose_syllable(ch)
        if syllable is not None:
            result.syllables.append(syllable)
            result.syllable_chars.append(ch)
        elif is_compat_jamo(ch):
            result.jamo.append(ch)
        # 그 외(문장부호/영문/숫자/이모지)는 음절/자모로 세지 않는다.

        if not ch.isspace():
            result.repetition_chars += ch

    result.exclaim_count = text.count("!")
    result.question_count = text.count("?")
    result.ellipsis_count = _count_ellipsis(text)
    return result
