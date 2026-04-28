from __future__ import annotations

from app.core.models import AnnotationTask, Prediction
from app.data.prodigy_jsonl import prediction_to_dict, task_to_dict


def task_to_label_studio_item(task: AnnotationTask, predictions: list[Prediction] | None = None) -> dict:
    """Build a minimal Label Studio-compatible import item.

    The canonical Rosetta format remains Prodigy-compatible JSONL. This adapter keeps
    Label Studio predictions as an edge format for future import/export bridges.
    """
    payload = task_to_dict(task)
    item = {
        "id": task.id,
        "data": {
            "text": task.text,
            "rosetta_task": payload,
        },
    }
    if predictions:
        item["predictions"] = [
            {
                "model_version": prediction.model or prediction.source,
                "score": prediction.score,
                "result": prediction_to_dict(prediction),
            }
            for prediction in predictions
        ]
    return item
