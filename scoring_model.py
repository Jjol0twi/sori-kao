"""카테고리 점수를 NumPy로 계산하고 Top-3·신뢰도를 산출한다(build-prompt §8).

점수식: ``category_scores = x @ W.T + bias + auxiliary_bonus``
"""

import json
import os
from dataclasses import dataclass, field

import numpy as np

from feature_extractor import FEATURE_NAMES, extract_features
from text_preprocessor import PreprocessResult, preprocess

# 카테고리 순서 고정(동점 타이브레이크·출력 정렬 기준) — build-prompt §3
CATEGORIES = [
    "응원", "기쁨", "당황", "분노", "긴장", "피곤", "장난", "사과", "감사", "집중",
]

# 자모 반복 패턴 → 보너스 대상 카테고리 — build-prompt §7
JAMO_PATTERNS = {
    "ㅋ": ["장난", "기쁨"],
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
    tie_categories: list             # 1위와 동점인 카테고리들(순서 고정)
    n: int                            # 분석 음절 수


class ScoringModel:
    """`category_weights.json`을 로드해 입력을 점수화한다."""

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
        self.min_syllables = meta["confidence"]["min_syllables"]
        self.score_gap_ratio = meta["confidence"]["score_gap_ratio"]

    def _auxiliary_bonus(self, text: str, jamo: list) -> dict:
        """키워드·자모 패턴 보너스를 카테고리별 합산하고 상한으로 자른다."""
        bonus = {c: 0.0 for c in CATEGORIES}
        for keyword, info in self.aux_keywords.items():
            if keyword in text:
                bonus[info["category"]] += info["bonus"]
        for jamo_char, categories in JAMO_PATTERNS.items():
            if jamo.count(jamo_char) >= JAMO_MIN_REPEAT:
                for category in categories:
                    bonus[category] += JAMO_PATTERN_BONUS
        return {c: min(b, self.aux_cap) for c, b in bonus.items()}

    def score(self, text: str, result: PreprocessResult = None) -> ScoreResult:
        """입력 문자열을 점수화해 :class:`ScoreResult`를 반환한다."""
        if result is None:
            result = preprocess(text)
        features = extract_features(result)

        aux = self._auxiliary_bonus(text, result.jamo)
        aux_vec = np.array([aux[c] for c in CATEGORIES], dtype=float)
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

        # 1위 카테고리 기여도(양수만, 내림차순)
        contrib = features * self.weights[top_idx]
        contributions = sorted(
            ((FEATURE_NAMES[i], float(contrib[i])) for i in range(len(FEATURE_NAMES))),
            key=lambda kv: kv[1],
            reverse=True,
        )
        contributions = [(name, val) for name, val in contributions if val > 0]

        confidence = self._confidence(result.n, ranked, features, aux, top_category)

        return ScoreResult(
            features=features,
            ranked=ranked,
            top3=ranked[:3],
            top_category=top_category,
            confidence=confidence,
            contributions=contributions,
            auxiliary={c: b for c, b in aux.items() if b > 0},
            tie_categories=tie,
            n=result.n,
        )

    def _confidence(self, n, ranked, features, aux, top_category) -> str:
        """신뢰도 high/low 판정 — build-prompt §8."""
        if n < self.min_syllables:
            return "low"
        top_score = ranked[0][1]
        second_score = ranked[1][1]
        if top_score <= 0:
            return "low"
        if (top_score - second_score) / top_score < self.score_gap_ratio:
            return "low"
        if features.sum() < 1e-9 and aux.get(top_category, 0) > 0:
            return "low"
        return "high"
