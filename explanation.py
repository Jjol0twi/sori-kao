"""음운 인상 해석 이유 문장을 생성한다.

실제 점수에 기여한 특징만 사용하고, 단정 대신 "점수 반영"으로 표현한다.
단독 자모 반복이 쓰였으면 표기 보조 신호로 표시하고, 신뢰도가 낮으면 완화한다.

설명은 모델을 그럴듯하게 포장하는 문장이 아니라, 어떤 규칙이 결과를 밀었는지
사용자와 보고서 독자가 확인할 수 있게 하는 방어 장치다.
"""

from dataclasses import dataclass, field

# 설명 문장은 점수에 실제로 등장한 특징과만 연결해 과잉 해석을 피한다.
EXPLANATION_TEMPLATES = {
    "bright_vowel_ratio": "밝은 모음 비율이 높아 밝음·가벼움 인상 점수가 반영되었습니다.",
    "dark_vowel_ratio": "어두운 모음 비율이 높아 어두움·무거움 인상 점수가 반영되었습니다.",
    "neutral_vowel_ratio": "중성 모음이 많아 방향성이 약한 인상으로 반영되었습니다.",
    "tense_consonant_ratio": "된소리 비율이 높아 강함·격렬함 인상 점수가 반영되었습니다.",
    "aspirated_consonant_ratio": "거센소리가 감지되어 강함·격렬함 인상 점수가 반영되었습니다.",
    "nasal_liquid_ratio": "비음·유음이 많아 부드러움·흐름 인상 점수가 반영되었습니다.",
    "final_stop_ratio": "불파 폐쇄음 받침(ㄱ·ㄷ·ㅂ류)이 있어 소리가 끊기는 막힘·단절감 인상 점수가 반영되었습니다.",
    "final_ng_ratio": "종성 ㅇ이 많아 소리가 울려 지속·여운 인상 점수가 반영되었습니다.",
    "final_sonorant_ratio": "공명음 받침(ㄴ·ㅁ·ㄹ)이 있어 울려 이어지는 부드러움·여운 인상 점수가 반영되었습니다.",
    "syllable_repetition": "같은 음절 패턴이 반복되어 반복·리듬 인상 점수가 반영되었습니다.",
    "char_repetition": "같은 문자가 반복되어 반복·리듬 인상 점수가 반영되었습니다.",
    "exclaim_energy": "느낌표가 감지되어 강함·격렬함 인상에 보조적으로 반영되었습니다.",
    "question_energy": "물음표가 감지되어 표기상 흔들림 신호로 보조 반영되었습니다.",
    "ellipsis_energy": "말줄임표가 감지되어 지속·여운 인상에 보조적으로 반영되었습니다.",
}

_AUX_SENTENCE = "완성형 음절이 아닌 자모 반복은 표기 보조 신호로만 반영되었습니다."
_RHYTHM_SENTENCE = "반복 표면 신호가 강해 반복·리듬 후보로 반영되었습니다."
_LOW_SIGNAL_SENTENCE = "뚜렷한 음운 신호가 적어 입력 정보가 부족하게 반영되었습니다."
_FALLBACK_SENTENCE = "뚜렷한 음운 신호가 적어 기본 해석 후보로 표시되었습니다."
_LOW_CONFIDENCE_NOTE = "신뢰도가 낮아 확정 대신 후보 해석으로 표시되었습니다."


@dataclass
class Explanation:
    category: str
    confidence: str
    reasons: list = field(default_factory=list)  # 2개 이상
    note: str = ""


def build_explanation(score_result) -> Explanation:
    """점수 결과를 사용자가 읽을 수 있는 근거 문장으로 낮춘다."""
    reasons = []
    contribution_names = [name for name, _ in score_result.contributions[:4]]
    for name, _ in score_result.contributions[:4]:
        sentence = EXPLANATION_TEMPLATES.get(name)
        if sentence:
            reasons.append(sentence)

    aux_used = score_result.auxiliary.get(score_result.top_category, 0) > 0
    aux_sources = getattr(score_result, "auxiliary_sources", {}).get(
        score_result.top_category, []
    )
    if aux_used and "jamo" in aux_sources:
        # 자모 보정도 숨기지 않는다. 이 프로젝트의 강점은 설명 가능성이다.
        reasons.append(_AUX_SENTENCE)
    if aux_used and not aux_sources:
        reasons.append(_AUX_SENTENCE)

    # 데모와 보고서에서 빈 설명이 나오지 않게 하되, 근거가 약하면 약하다고 말한다.
    if not reasons:
        reasons.append(_LOW_SIGNAL_SENTENCE)
    if (
        score_result.top_category == "반복·리듬"
        and len(reasons) < 2
        and {"syllable_repetition", "char_repetition"} & set(contribution_names)
    ):
        reasons.append(_RHYTHM_SENTENCE)
    if len(reasons) < 2:
        reasons.append(_FALLBACK_SENTENCE)

    note = _LOW_CONFIDENCE_NOTE if score_result.confidence == "low" else ""
    return Explanation(
        category=score_result.top_category,
        confidence=score_result.confidence,
        reasons=reasons[:4],
        note=note,
    )
