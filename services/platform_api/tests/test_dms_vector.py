from __future__ import annotations

import math

import pytest
from app.dms_vector import DmsVectorError, chunk_document, local_embedding


def cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def test_local_embedding_is_stable_normalized_and_domain_aware() -> None:
    first = local_embedding("Wareneingang Stichprobe Prüfplan")
    second = local_embedding("Wareneingang Stichprobe Prüfplan")
    related = local_embedding("Qualität Prüfung einer eingehenden Lieferung")
    unrelated = local_embedding("Urlaubsantrag und Anwesenheitskalender")

    assert first == second
    assert len(first) == 768
    assert math.sqrt(sum(value * value for value in first)) == pytest.approx(1.0)
    assert cosine(first, related) > cosine(first, unrelated)


def test_local_embedding_rejects_empty_text_and_wrong_dimension() -> None:
    with pytest.raises(DmsVectorError, match="empty"):
        local_embedding("  ")
    with pytest.raises(DmsVectorError, match="768"):
        local_embedding("Prüfplan", dimensions=32)


def test_chunk_document_is_bounded_and_overlapping() -> None:
    chunks = chunk_document(" ".join(f"Abschnitt-{index}." for index in range(400)))

    assert len(chunks) > 1
    assert all(0 < len(chunk) <= 1400 for chunk in chunks)
    assert chunks[0][-80:] in chunks[1]
