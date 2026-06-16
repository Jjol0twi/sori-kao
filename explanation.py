"""추천 이유 문장을 생성한다(build-prompt §12, design.md §10).

실제 점수에 기여한 특징만 사용하고, 단정 대신 "점수 반영"으로 표현한다.
보조 키워드/자모가 쓰였으면 보조 신호로 표시하고, 신뢰도가 낮으면 완화한다.
"""

from dataclasses import dataclass, field

# 특징 → 설명 문장(design.md §10 확장). 점수에 실제로 기여한 특징만 쓴다.
EXPLANATION_TEMPLATES = {
    "bright_vowel_ratio": "밝은 모음 비율이 높아 긍정적·가벼운 인상 점수가 올라갔습니다.",
    "dark_vowel_ratio": "어두운 모음 비율이 높아 무겁거나 지친 인상 점수가 반영되었습니다.",
    "neutral_vowel_ratio": "중성 모음이 많아 방향성이 약한 인상으로 반영되었습니다.",
    "tense_consonant_ratio": "된소리 비율이 높아 강한 감정 표현으로 해석되었습니다.",
    "aspirated_consonant_ratio": "거센소리가 감지되어 에너지와 반응 강도가 올라갔습니다.",
    "nasal_liquid_ratio": "비음·유음이 많아 부드럽거나 울리는 인상으로 반영되었습니다.",
    "final_consonant_density": "받침이 많아 단단하거나 눌린 인상 점수가 반영되었습니다.",
    "final_ng_ratio": "종성 ㅇ이 많아 울림 있는 인상으로 반영되었습니다.",
    "final_s_ratio": "종성 ㅅ이 많아 끊기거나 날카로운 인상으로 반영되었습니다.",
    "syllable_repetition": "같은 음절 패턴이 반복되어 강조와 리듬감이 감지되었습니다.",
    "char_repetition": "같은 문자가 반복되어 강조·지속 신호가 감지되었습니다.",
    "exclaim_energy": "느낌표가 감지되어 에너지·강조 점수가 올라갔습니다.",
    "question_energy": "물음표가 감지되어 의문·당황 점수가 반영되었습니다.",
    "ellipsis_energy": "말줄임표가 감지되어 머뭇거림·여운 점수가 반영되었습니다.",
}

_AUX_SENTENCE = "보조 신호(키워드·자모)가 감지되어 보조적으로 반영되었습니다."
_FALLBACK_SENTENCE = "뚜렷한 음운 신호가 적어 기본 후보로 추천되었습니다."
_LOW_CONFIDENCE_NOTE = "신뢰도가 낮아 확정 대신 후보로 추천되었습니다."


@dataclass
class Explanation:
    category: str
    confidence: str
    reasons: list = field(default_factory=list)  # 2개 이상
    note: str = ""


def build_explanation(score_result) -> Explanation:
    """:class:`ScoreResult`에서 추천 이유를 만든다(이유 2개 이상 보장)."""
    reasons = []
    for name, _ in score_result.contributions[:4]:
        sentence = EXPLANATION_TEMPLATES.get(name)
        if sentence:
            reasons.append(sentence)

    aux_used = score_result.auxiliary.get(score_result.top_category, 0) > 0
    if aux_used:
        reasons.append(_AUX_SENTENCE)

    # 이유 2개 이상 보장(완료 기준)
    if len(reasons) < 2:
        reasons.append(_FALLBACK_SENTENCE)

    note = _LOW_CONFIDENCE_NOTE if score_result.confidence == "low" else ""
    return Explanation(
        category=score_result.top_category,
        confidence=score_result.confidence,
        reasons=reasons[:4],
        note=note,
    )
