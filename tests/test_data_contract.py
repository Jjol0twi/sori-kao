"""JSON 데이터가 코드의 고정 계약과 맞는지 검증한다."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feature_extractor import FEATURE_NAMES
from recommender import SIZES
from scoring_model import CATEGORIES

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_json(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def test_category_weights_match_feature_contract():
    config = _load_json("data/category_weights.json")
    assert config["_meta"]["feature_order"] == FEATURE_NAMES
    assert list(config["categories"]) == CATEGORIES

    for category in CATEGORIES:
        item = config["categories"][category]
        assert len(item["weights"]) == len(FEATURE_NAMES)
        assert all(isinstance(weight, (int, float)) for weight in item["weights"])
        assert isinstance(item["bias"], (int, float))


def test_auxiliary_keywords_reference_known_categories_and_cap():
    config = _load_json("data/category_weights.json")
    cap = config["_meta"]["auxiliary_bonus_cap"]

    for keyword, item in config["auxiliary_keywords"].items():
        assert keyword
        assert item["category"] in CATEGORIES
        assert 0 < item["bonus"] <= cap


def test_auxiliary_patterns_reference_known_categories_and_cap():
    config = _load_json("data/category_weights.json")
    cap = config["_meta"]["conventional_bonus_cap"]

    for pattern, item in config["auxiliary_patterns"].items():
        assert pattern
        re.compile(pattern)
        assert item["category"] in CATEGORIES
        assert 0 < item["bonus"] <= cap


def test_kaomoji_catalog_has_required_sizes():
    catalog = _load_json("data/kaomoji_catalog.json")
    assert set(catalog) - {"_meta"} == set(CATEGORIES)

    for category in CATEGORIES:
        entries = catalog[category]
        sizes = {entry["size"] for entry in entries}
        assert set(SIZES).issubset(sizes)
        assert all(entry["text"] for entry in entries)
