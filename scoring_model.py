"""카테고리 점수를 NumPy로 계산하고 Top-3·신뢰도를 산출한다.

점수식: ``category_scores = x @ W.T + bias + auxiliary_bonus``

음운 벡터, 채팅 관습, 제한적인 의미 힌트를 여기서만 합쳐서 "AI 해석"이 아니라
추적 가능한 규칙 점수로 남긴다.
"""

import json
import os
import re
from dataclasses import dataclass

import numpy as np

from feature_extractor import FEATURE_NAMES, extract_features
from text_preprocessor import PreprocessResult, preprocess

# 카테고리 순서는 동점 타이브레이크와 출력 정렬 기준으로 고정한다.
CATEGORIES = [
    "응원", "기쁨", "당황", "분노", "긴장", "피곤", "장난", "사과", "감사", "집중",
]

# ㅋㅋ/ㅠㅠ 같은 단독 자모는 음운 분해 대상이 아니라 채팅에서 굳어진 표현 신호로 본다.
JAMO_PATTERNS = {
    "ㅋ": ["장난"],
    "ㅎ": ["기쁨", "감사"],
    "ㅠ": ["피곤", "긴장", "사과"],
    "ㅜ": ["피곤", "긴장", "사과"],
    "ㄷ": ["당황", "긴장"],
}
JAMO_PATTERN_BONUS = 0.3  # 자모 패턴 1건당 보너스(heuristic_initial)
JAMO_MIN_REPEAT = 2       # 자모가 2회 이상이면 반복으로 본다

_DEFAULT_CONFIG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "category_weights.json"
)


@dataclass
class ScoreResult:
    features: np.ndarray
    ranked: list                      # (category, score) 내림차순
    top3: list                        # 상위 3개 (category, score)
    top_category: str
    confidence: str                   # "high" | "low"
    contributions: list              # 1위 카테고리의 (feature, 기여도) 내림차순(양수만)
    auxiliary: dict                   # 카테고리별 적용된 보너스(상한 반영)
    auxiliary_sources: dict           # 카테고리별 보조 신호 출처
    tie_categories: list             # 1위와 동점인 카테고리들(순서 고정)
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
        )  # (10, 14)
        self.bias = np.array(
            [config["categories"][c]["bias"] for c in CATEGORIES], dtype=float
        )  # (10,)
        self.aux_keywords = config["auxiliary_keywords"]
        self.aux_cap = meta["auxiliary_bonus_cap"]
        self.semantic_hints = config.get("semantic_hints", {})
        self.semantic_cap = meta.get("semantic_bonus_cap", self.aux_cap)
        self.min_syllables = meta["confidence"]["min_syllables"]
        self.score_gap_ratio = meta["confidence"]["score_gap_ratio"]

    def _auxiliary_bonus(self, text: str, jamo: list) -> dict:
        """음운만으로 구분하기 어려운 관습 신호를 제한된 보너스로만 보탠다."""
        bonus = {c: 0.0 for c in CATEGORIES}
        sources = {c: [] for c in CATEGORIES}

        def add_source(category: str, source: str) -> None:
            if source not in sources[category]:
                sources[category].append(source)

        for keyword, info in self.aux_keywords.items():
            if keyword in text:
                # 감사/미안처럼 명시적인 표현은 시연 안정성을 위해 약하게 보정한다.
                bonus[info["category"]] += info["bonus"]
                add_source(info["category"], "keyword")
        for jamo_char, categories in JAMO_PATTERNS.items():
            if jamo.count(jamo_char) >= JAMO_MIN_REPEAT:
                for category in categories:
                    # 자모 반복은 소리값보다 채팅 관습에 가까우므로 출처를 따로 남긴다.
                    bonus[category] += JAMO_PATTERN_BONUS
                    add_source(category, "jamo")
        bonus = {c: min(b, self.aux_cap) for c, b in bonus.items()}
        for tag, info in self.semantic_hints.items():
            if any(re.search(pattern, text) for pattern in info["patterns"]):
                for category, category_bonus in info["category_bonus"].items():
                    # 하암/망할처럼 음운만으로 오판하기 쉬운 표현은 태그 단위로만 보정한다.
                    bonus[category] = min(
                        bonus[category] + category_bonus, self.semantic_cap
                    )
                    add_source(category, f"semantic:{tag}")
        return bonus, sources

    def score(self, text: str, result: PreprocessResult = None) -> ScoreResult:
        """분리되어 있던 음운·보조 신호를 최종 카테고리 점수로 합친다."""
        if result is None:
            result = preprocess(text)
        features = extract_features(result)

        aux, aux_sources = self._auxiliary_bonus(text, result.jamo)
        aux_vec = np.array([aux[c] for c in CATEGORIES], dtype=float)
        # 최종 점수 합성은 이 한 줄에 모아 두어, 설명과 테스트가 같은 근거를 보게 한다.
        scores = self.weights @ features + self.bias + aux_vec

        # 점수 내림차순, 동점은 CATEGORIES 순서로 타이브레이크
        order = sorted(range(len(CATEGORIES)), key=lambda i: (-scores[i], i))
        ranked = [(CATEGORIES[i], float(scores[i])) for i in order]
        top_idx = order[0]
        top_category = CATEGORIES[top_idx]
        top_score = scores[top_idx]

        # 점수가 모두 0 이하인 퇴화 입력(자모/숫자만 등)은 가짜 동점을 만들지 않는다
        if top_score > 0:
            tie = [c for c, s in ranked if s == top_score]
        else:
            tie = [top_category]

        # 추천 이유는 실제 양수 기여도에서만 고른다. 없는 근거를 문장으로 꾸미지 않기 위해서다.
        contrib = features * self.weights[top_idx]
        contributions = sorted(
            ((FEATURE_NAMES[i], float(contrib[i])) for i in range(len(FEATURE_NAMES))),
            key=lambda kv: kv[1],
            reverse=True,
        )
        contributions = [(name, val) for name, val in contributions if val > 0]

        confidence = self._confidence(result.n, ranked, features, aux, top_idx)

        return ScoreResult(
            features=features,
            ranked=ranked,
            top3=ranked[:3],
            top_category=top_category,
            confidence=confidence,
            contributions=contributions,
            auxiliary={c: b for c, b in aux.items() if b > 0},
            auxiliary_sources={c: aux_sources[c] for c, b in aux.items() if b > 0},
            tie_categories=tie,
            n=result.n,
        )

    def _confidence(self, n, ranked, features, aux, top_idx) -> str:
        """점수는 내되, 근거가 약한 추천은 낮은 신뢰도로 드러낸다."""
        if n < self.min_syllables:
            return "low"
        top_score = ranked[0][1]
        second_score = ranked[1][1]
        if top_score <= 0:  # 점수가 비양수면 비율 판정 불가 → 모호로 본다(0-나눗셈 가드)
            return "low"
        if (top_score - second_score) / top_score < self.score_gap_ratio:
            return "low"
        # 보조 신호가 음운 점수보다 크면 "소리 인상"보다 관습 보정이 결과를 좌우한 것이다.
        top_category = CATEGORIES[top_idx]
        aux_top = aux.get(top_category, 0)
        phonetic_top = float(self.weights[top_idx] @ features + self.bias[top_idx])
        if aux_top > 0 and phonetic_top < aux_top:
            return "low"
        return "high"
