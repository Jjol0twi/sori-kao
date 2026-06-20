"""음운 인상 점수를 NumPy로 계산하고 Top-3·신뢰도를 산출한다.

점수식: ``category_scores = x @ W.T + bias + auxiliary_bonus``

완성형 한글에서 얻은 음운 벡터를 중심으로 해석하고, 단독 자모 반복은
표기 보조 신호로만 제한해 "AI 해석"이 아니라 추적 가능한 규칙 점수로 남긴다.
"""

import json
import os
import sys
from dataclasses import dataclass

import numpy as np

from feature_extractor import FEATURE_NAMES, extract_features
from text_preprocessor import PreprocessResult, preprocess

# 인상 축 순서는 동점 타이브레이크와 출력 정렬 기준으로 고정한다.
CATEGORIES = [
    "밝음·가벼움",
    "어두움·무거움",
    "작음·섬세함",
    "큼·둔중함",
    "강함·격렬함",
    "부드러움·흐름",
    "반복·리듬",
    "지속·여운",
    "막힘·단절감",
]

# ㅋㅋ/ㅠㅠ 같은 단독 자모는 의미 단어가 아니라 반복된 표기라는 약한 신호로 본다.
JAMO_PATTERNS = {
    "ㅋ": {"반복·리듬": 0.5},
    "ㅎ": {"반복·리듬": 0.5},
    "ㅠ": {"반복·리듬": 0.3, "지속·여운": 0.5},
    "ㅜ": {"반복·리듬": 0.3, "지속·여운": 0.5},
}
JAMO_MIN_REPEAT = 2       # 자모가 2회 이상이면 반복으로 본다

# PyInstaller로 .app 번들이 되면 데이터가 sys._MEIPASS 아래에 풀린다(개발 모드는 파일 위치).
_DATA_DIR = os.path.join(
    getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "data"
)
_DEFAULT_CONFIG = os.path.join(_DATA_DIR, "category_weights.json")


@dataclass
class ScoreResult:
    features: np.ndarray
    ranked: list                      # (인상 축, score) 내림차순
    top3: list                        # 상위 3개 (인상 축, score)
    top_category: str
    confidence: str                   # "high" | "low"
    weak_signal: bool                 # 정보량(유표) 신호가 약함 → "뚜렷한 음운 인상 없음"
    contributions: list              # 1위 축의 (feature, 기여도) 내림차순(양수만)
    auxiliary: dict                   # 축별 적용된 표기 보조 보너스(상한 반영)
    auxiliary_sources: dict           # 축별 보조 신호 출처
    tie_categories: list             # 1위와 동점인 축들(순서 고정)
    n: int                            # 분석 음절 수


class ScoringModel:
    """문서에 적은 규칙과 JSON 가중치를 실행 가능한 점수식으로 연결한다."""

    def __init__(self, config_path: str = _DEFAULT_CONFIG):
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        meta = config["_meta"]
        if meta["feature_order"] != FEATURE_NAMES:
            raise ValueError("feature_order가 FEATURE_NAMES와 일치하지 않는다.")

        self.weights = np.array(
            [config["categories"][c]["weights"] for c in CATEGORIES], dtype=float
        )  # (9, 14)
        self.bias = np.array(
            [config["categories"][c]["bias"] for c in CATEGORIES], dtype=float
        )
        # 정보량(markedness) 가중: 자질을 한국어 출현빈도 역수로 눌러, 흔한 모음(ㅏ 등)의
        # 과대 기여를 막고 드문 유표 자질(된소리·첩어 등)을 부각한다(빈도 근거 추정값).
        info = meta.get("informativeness")
        self.informativeness = (
            np.array(info, dtype=float) if info else np.ones(len(FEATURE_NAMES))
        )
        self.aux_cap = meta["auxiliary_bonus_cap"]
        self.min_syllables = meta["confidence"]["min_syllables"]
        # 정보량 가중 점수의 top이 이 값 미만이고 자모 패턴도 없으면 '뚜렷한 음운 인상 없음'.
        self.weak_threshold = meta["confidence"].get("weak_signal_threshold", 0.0)

    def _auxiliary_bonus(self, text: str, jamo: list) -> dict:
        """단독 자모 반복을 표기 보조 신호로만 제한해 보탠다."""
        bonus = {c: 0.0 for c in CATEGORIES}
        sources = {c: [] for c in CATEGORIES}

        def add_source(category: str, source: str) -> None:
            if source not in sources[category]:
                sources[category].append(source)

        for jamo_char, categories in JAMO_PATTERNS.items():
            if jamo.count(jamo_char) >= JAMO_MIN_REPEAT:
                for category, category_bonus in categories.items():
                    bonus[category] += category_bonus
                    add_source(category, "jamo")

        # 특정 자모 의미를 해석하지 않더라도, 같은 자모가 반복되면 리듬 표기로만 낮게 반영한다.
        if not any(sources.values()):
            repeated_jamo = any(jamo.count(ch) >= JAMO_MIN_REPEAT for ch in set(jamo))
            if repeated_jamo:
                bonus["반복·리듬"] += 0.25
                add_source("반복·리듬", "jamo")

        bonus = {c: min(b, self.aux_cap) for c, b in bonus.items()}
        return bonus, sources

    def score(self, text: str, result: PreprocessResult = None) -> ScoreResult:
        """분리되어 있던 음운·표기 보조 신호를 최종 인상 점수로 합친다."""
        if result is None:
            result = preprocess(text)
        features = extract_features(result)
        weighted = features * self.informativeness  # 정보량(markedness) 가중

        aux, aux_sources = self._auxiliary_bonus(text, result.jamo)
        aux_vec = np.array([aux[c] for c in CATEGORIES], dtype=float)
        # 최종 점수 합성은 이 한 줄에 모아 두어, 설명과 테스트가 같은 근거를 보게 한다.
        scores = self.weights @ weighted + self.bias + aux_vec

        # 점수 내림차순, 동점은 CATEGORIES 순서로 타이브레이크한다.
        order = sorted(range(len(CATEGORIES)), key=lambda i: (-scores[i], i))
        ranked = [(CATEGORIES[i], float(scores[i])) for i in order]
        top_idx = order[0]
        top_category = CATEGORIES[top_idx]
        top_score = scores[top_idx]

        # 점수가 모두 0 이하인 퇴화 입력(숫자만 등)은 가짜 동점을 만들지 않는다.
        if top_score > 0:
            tie = [c for c, s in ranked if s == top_score]
        else:
            tie = [top_category]

        # 해석 이유는 실제 양수 기여도에서만 고른다. 없는 근거를 문장으로 꾸미지 않기 위해서다.
        # 점수와 같은 정보량 가중 기여를 쓴다(설명이 실제 점수 근거와 일치).
        contrib = weighted * self.weights[top_idx]
        contributions = sorted(
            ((FEATURE_NAMES[i], float(contrib[i])) for i in range(len(FEATURE_NAMES))),
            key=lambda kv: kv[1],
            reverse=True,
        )
        contributions = [(name, val) for name, val in contributions if val > 0]

        # 정보량 가중 top이 임계 미만이고 자모 패턴(보조 신호)도 없으면 약신호로 본다.
        has_pattern = any(b > 0 for b in aux.values())
        weak = bool(top_score < self.weak_threshold and not has_pattern)
        confidence = self._confidence(result.n, ranked, weighted, aux, top_idx, weak)

        return ScoreResult(
            features=features,
            ranked=ranked,
            top3=ranked[:3],
            top_category=top_category,
            confidence=confidence,
            weak_signal=weak,
            contributions=contributions,
            auxiliary={c: b for c, b in aux.items() if b > 0},
            auxiliary_sources={c: aux_sources[c] for c, b in aux.items() if b > 0},
            tie_categories=tie,
            n=result.n,
        )

    def _confidence(self, n, ranked, weighted, aux, top_idx, weak) -> str:
        """점수는 내되, 근거가 약한 해석은 낮은 신뢰도로 드러낸다."""
        if n < self.min_syllables:
            return "low"
        if weak:  # 정보량(유표) 신호가 임계 미만 → 뚜렷한 음운 인상 없음
            return "low"
        top_score = ranked[0][1]
        if top_score <= 0:  # 점수가 비양수면 비율 판정 불가 → 모호로 본다(0-나눗셈 가드)
            return "low"
        # 보조 신호가 음운 점수보다 크면 "소리 인상"보다 표기 보정이 결과를 좌우한 것이다.
        top_category = CATEGORIES[top_idx]
        aux_top = aux.get(top_category, 0)
        phonetic_top = float(self.weights[top_idx] @ weighted + self.bias[top_idx])
        if aux_top > 0 and phonetic_top < aux_top:
            return "low"
        return "high"
