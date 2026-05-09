from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any


def score_markdown(markdown: str, expected_keywords: Iterable[str]) -> float:
    if not markdown.strip():
        return 0.0
    length_score = min(len(markdown) / 8000, 1.0) * 0.35
    structure_score = min(
        (
            markdown.count("#")
            + markdown.count("|")
            + markdown.lower().count("table")
            + markdown.lower().count("figure")
        )
        / 30,
        1.0,
    ) * 0.25
    keyword_score = _keyword_ratio(markdown, expected_keywords) * 0.4
    return round(length_score + structure_score + keyword_score, 4)


def score_context(context: str, expected_keywords: Iterable[str]) -> float:
    if not context.strip():
        return 0.0
    coverage = _keyword_ratio(context, expected_keywords)
    density = min(len(context) / 4000, 1.0)
    return round(coverage * 0.7 + density * 0.3, 4)


def score_answer(answer: str | dict[str, Any], expected_keywords: Iterable[str]) -> float:
    text = answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)
    if not text.strip():
        return 0.0
    keyword_score = _keyword_ratio(text, expected_keywords) * 0.55
    citation_score = 0.25 if re.search(r"citation|source|url|http|obj_", text, re.I) else 0.0
    confidence_score = 0.20
    if isinstance(answer, dict):
        confidence = answer.get("confidence")
        if isinstance(confidence, int | float):
            confidence_score = max(0.0, min(float(confidence), 1.0)) * 0.20
    return round(keyword_score + citation_score + confidence_score, 4)


def _keyword_ratio(text: str, keywords: Iterable[str]) -> float:
    tokens = [keyword.lower() for keyword in keywords if keyword]
    if not tokens:
        return 0.0
    lower = text.lower()
    hits = sum(1 for keyword in tokens if keyword in lower)
    return hits / len(tokens)
