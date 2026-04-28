from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Iterable

from app.core.models import AnnotationTask
from app.data.prodigy_jsonl import task_from_dict

SENTENCE_PATTERN = re.compile(r"[^。！？!?；;\.\n]+[。！？!?；;\.]?", re.MULTILINE)
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]|[^\s]", re.UNICODE)


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for paragraph_index, paragraph in enumerate(text.splitlines()):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        matches = [match.group(0).strip() for match in SENTENCE_PATTERN.finditer(paragraph)]
        for sentence in matches:
            if sentence:
                sentences.append(sentence)
        if not matches:
            sentences.append(paragraph)
    return sentences


def tokenize_text(text: str) -> list[dict]:
    tokens: list[dict] = []
    for index, match in enumerate(TOKEN_PATTERN.finditer(text)):
        tokens.append(
            {
                "id": index,
                "text": match.group(0),
                "start": match.start(),
                "end": match.end(),
            }
        )
    return tokens


def tasks_from_txt(text: str, source_name: str = "uploaded.txt", prefix: str = "txt") -> list[AnnotationTask]:
    tasks: list[AnnotationTask] = []
    for index, sentence in enumerate(split_sentences(text), start=1):
        task = AnnotationTask(
            id=f"{prefix}-{index:05d}",
            text=sentence,
            tokens=tuple(tokenize_text(sentence)),
            meta={"source": source_name, "source_format": "txt", "sentence_index": index},
        )
        task.validate()
        tasks.append(task)
    return tasks


def tasks_from_jsonl(content: str, source_name: str = "uploaded.jsonl", prefix: str = "jsonl") -> list[AnnotationTask]:
    tasks: list[AnnotationTask] = []
    for index, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if "id" not in row:
            row["id"] = f"{prefix}-{index:05d}"
        if "text" not in row:
            raise ValueError(f"JSONL 第 {index} 行缺少 text 字段")
        row.setdefault("tokens", tokenize_text(str(row["text"])))
        row.setdefault("spans", [])
        row.setdefault("relations", [])
        row.setdefault("options", [])
        row.setdefault("accept", [])
        row.setdefault("answer", None)
        row.setdefault("meta", {})
        row["meta"] = {**dict(row.get("meta", {})), "source": source_name, "source_format": "jsonl"}
        tasks.append(task_from_dict(row))
    return tasks


def tasks_from_csv(
    content: str,
    text_column: str,
    source_name: str = "uploaded.csv",
    prefix: str = "csv",
) -> list[AnnotationTask]:
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames or text_column not in reader.fieldnames:
        raise ValueError(f"CSV 缺少文本列: {text_column}")
    tasks: list[AnnotationTask] = []
    for index, row in enumerate(reader, start=1):
        text = str(row.get(text_column, "")).strip()
        if not text:
            continue
        meta = {key: value for key, value in row.items() if key != text_column}
        meta.update({"source": source_name, "source_format": "csv", "row_index": index})
        task = AnnotationTask(
            id=f"{prefix}-{index:05d}",
            text=text,
            tokens=tuple(tokenize_text(text)),
            meta=meta,
        )
        task.validate()
        tasks.append(task)
    return tasks


def tasks_from_path(path: str | Path, text_column: str | None = None) -> list[AnnotationTask]:
    source = Path(path)
    content = source.read_text(encoding="utf-8")
    suffix = source.suffix.lower()
    if suffix == ".txt":
        return tasks_from_txt(content, source_name=source.name)
    if suffix == ".jsonl":
        return tasks_from_jsonl(content, source_name=source.name)
    if suffix == ".csv":
        return tasks_from_csv(content, text_column=text_column or "text", source_name=source.name)
    raise ValueError(f"不支持的文件类型: {source.suffix}")


def preview_tasks(tasks: Iterable[AnnotationTask], limit: int = 5) -> list[dict]:
    preview: list[dict] = []
    for task in list(tasks)[:limit]:
        preview.append({"id": task.id, "text": task.text, "token_count": len(task.tokens), "meta": task.meta})
    return preview
