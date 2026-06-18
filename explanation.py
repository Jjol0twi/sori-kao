"""추천 이유 문장을 생성한다.

실제 점수에 기여한 특징만 사용하고, 단정 대신 "점수 반영"으로 표현한다.
보조 키워드/자모/관습 표현이 쓰였으면 보조 신호로 표시하고, 신뢰도가 낮으면 완화한다.

설명은 모델을 그럴듯하게 포장하는 문장이 아니라, 어떤 규칙이 결과를 밀었는지
사용자와 보고서 독자가 확인할 수 있게 하는 방어 장치다.
"""

from dataclasses import dataclass, field

# 설명 문장은 점수에 실제로 등장한 특징과만 연결해 과잉 해석을 피한다.
EXPLANATION_TEMPLATES = {
    "bright_vowel_ratio": "밝은 모음 비율이 높아 긍정적·가벼운 인상 점수가 올라갔습니다.",
    "dark_vowel_ratio": "어두운 모음 비율이 높아 무겁거나 지친 인상 점수가 반영되었습니다.",
    "neutral_vowel_ratio": "중성 모음이 많아 방향성이 약한 인상으로 반영되었습니다.",
    "tense_consonant_ratio": "된소리 비율이 높아 강한 감정 표현으로 해석되었습니다.",
    "aspirated_consonant_ratio": "거센소리가 감지되어 에너지와 반응 강도가 올라갔습니다.",
    "nasal_liquid_ratio": "비음·유음이 많아 부드럽거나 울리는 인상으로 반영되었습니다.",
    "final_consonant_density": "받침이 많아 단단하거나 눌린 인상 점수가 반영되었습니다.",
    "final_ng_ratio": "종성 ㅇ이 많아 울림 있는 인상으로 반영되었습니다.",
    "final_s_ratio": "종성 ㅅ·ㅆ이 많아 끊기거나 날카로운 인상으로 반영되었습니다.",
    "syllable_repetition": "같은 음절 패턴이 반복되어 강조와 리듬감이 감지되었습니다.",
    "char_repetition": "같은 문자가 반복되어 강조·지속 신호가 감지되었습니다.",
    "exclaim_energy": "느낌표가 감지되어 에너지·강조 점수가 올라갔습니다.",
    "question_energy": "물음표가 감지되어 의문·당황 점수가 반영되었습니다.",
    "ellipsis_energy": "말줄임표가 감지되어 머뭇거림·여운 점수가 반영되었습니다.",
}

_AUX_SENTENCE = "보조 신호(키워드·자모)가 감지되어 보조적으로 반영되었습니다."
_CONVENTIONAL_SENTENCE = "관습 표현 보조 신호가 감지되어 음운 점수와 별도로 반영되었습니다."
_CONVENTIONAL_LIMIT_SENTENCE = "소리 특징만으로는 관습적 의미를 구분하기 어려워 신뢰도를 낮게 표시합니다."
_RHYTHM_PLAY_SENTENCE = "반복 리듬이 강해 가벼운 장난·의태어 후보로 반영되었습니다."
_LOW_SIGNAL_SENTENCE = "뚜렷한 음운 신호가 적어 입력 정보가 부족하게 반영되었습니다."
_FALLBACK_SENTENCE = "뚜렷한 음운 신호가 적어 기본 후보로 추천되었습니다."
_LOW_CONFIDENCE_NOTE = "신뢰도가 낮아 확정 대신 후보로 추천되었습니다."


def _has_semantic_source(sources):
    return any(source.startswith("semantic:") for source in sources)


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
    semantic_used = _has_semantic_source(aux_sources)
    if semantic_used:
        # 의미 힌트가 개입한 경우, 순수 음운 추천처럼 보이지 않도록 명시한다.
        reasons.append(_CONVENTIONAL_SENTENCE)
    if aux_used and ({source for source in aux_sources} & {"keyword", "jamo"}):
        # 키워드·자모 보정도 숨기지 않는다. 이 프로젝트의 강점은 설명 가능성이다.
        reasons.append(_AUX_SENTENCE)
    if aux_used and not aux_sources:
        reasons.append(_AUX_SENTENCE)

    # 데모와 보고서에서 빈 설명이 나오지 않게 하되, 근거가 약하면 약하다고 말한다.
    if not reasons:
        reasons.append(_LOW_SIGNAL_SENTENCE)
    if semantic_used and len(reasons) < 2:
        reasons.append(_CONVENTIONAL_LIMIT_SENTENCE)
    if (
        score_result.top_category == "장난"
        and len(reasons) < 2
        and {"syllable_repetition", "char_repetition"} & set(contribution_names)
    ):
        reasons.append(_RHYTHM_PLAY_SENTENCE)
    if len(reasons) < 2:
        reasons.append(_FALLBACK_SENTENCE)

    note = _LOW_CONFIDENCE_NOTE if score_result.confidence == "low" else ""
    return Explanation(
        category=score_result.top_category,
        confidence=score_result.confidence,
        reasons=reasons[:4],
        note=note,
    )
