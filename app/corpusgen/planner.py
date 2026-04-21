from __future__ import annotations

from app.corpusgen.contracts import CorpusGenre, CorpusSpec, GenerationTask, MemoryRecord


def plan_generation_tasks(spec: CorpusSpec, memory_records: list[MemoryRecord]) -> list[GenerationTask]:
    task_count = spec.task_count
    genre_allocations = _allocate_genre_tasks(task_count, spec.genres)
    focus_pool = _build_focus_pool(memory_records)

    tasks: list[GenerationTask] = []
    remaining_samples = spec.total_samples
    focus_index = 0
    task_index = 1

    for genre in spec.genres:
        allocation = genre_allocations[genre.name]
        for _ in range(allocation):
            target_count = min(spec.samples_per_task, remaining_samples)
            if target_count <= 0:
                break

            focus = focus_pool[focus_index % len(focus_pool)]
            focus_index += 1
            query = " ".join(
                part
                for part in [spec.domain, spec.language, genre.name, focus]
                if part and part.strip()
            )
            tasks.append(
                GenerationTask(
                    task_id=f"{spec.name}-task-{task_index:03d}",
                    genre_name=genre.name,
                    focus=focus,
                    query=query,
                    instruction=genre.instruction,
                    style=genre.style,
                    difficulty=genre.difficulty,
                    target_count=target_count,
                    metadata={"genre_weight": genre.weight},
                )
            )
            task_index += 1
            remaining_samples -= target_count

    return tasks


def generation_task_to_dict(task: GenerationTask) -> dict:
    return {
        "task_id": task.task_id,
        "genre_name": task.genre_name,
        "focus": task.focus,
        "query": task.query,
        "instruction": task.instruction,
        "style": task.style,
        "difficulty": task.difficulty,
        "target_count": task.target_count,
        "metadata": task.metadata,
    }


def generation_task_from_dict(payload: dict) -> GenerationTask:
    return GenerationTask(
        task_id=str(payload["task_id"]),
        genre_name=str(payload["genre_name"]),
        focus=str(payload["focus"]),
        query=str(payload["query"]),
        instruction=str(payload["instruction"]),
        style=str(payload["style"]),
        difficulty=str(payload.get("difficulty", "mixed")),
        target_count=int(payload.get("target_count", 1)),
        metadata=dict(payload.get("metadata", {})),
    )


def _allocate_genre_tasks(task_count: int, genres: tuple[CorpusGenre, ...]) -> dict[str, int]:
    total_weight = sum(genre.weight for genre in genres)
    raw = [task_count * genre.weight / total_weight for genre in genres]
    base = [int(value) for value in raw]
    allocated = sum(base)
    remainders = sorted(
        ((raw[index] - base[index], index) for index in range(len(genres))),
        reverse=True,
    )
    for _, index in remainders[: task_count - allocated]:
        base[index] += 1
    return {genre.name: count for genre, count in zip(genres, base, strict=True)}


def _build_focus_pool(memory_records: list[MemoryRecord]) -> list[str]:
    pool: list[str] = []
    seen: set[str] = set()
    for record in memory_records:
        candidates = list(record.tags)
        if not candidates:
            candidates = [record.title]
        for candidate in candidates:
            normalized = candidate.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                pool.append(normalized)
    return pool or ["general"]
