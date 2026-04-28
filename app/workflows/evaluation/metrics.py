from __future__ import annotations

from app.core.models import AnnotationSpan


def span_f1(gold: tuple[AnnotationSpan, ...], predicted: tuple[AnnotationSpan, ...]) -> dict[str, float]:
    gold_set = {(span.start, span.end, span.label) for span in gold}
    predicted_set = {(span.start, span.end, span.label) for span in predicted}
    true_positive = len(gold_set & predicted_set)
    precision = true_positive / len(predicted_set) if predicted_set else 0.0
    recall = true_positive / len(gold_set) if gold_set else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }
