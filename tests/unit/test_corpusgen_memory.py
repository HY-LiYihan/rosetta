import json
import tempfile
import unittest
from pathlib import Path

from app.corpusgen.memory.compression import build_context_pack
from app.corpusgen.memory.layers import build_memory_records
from app.corpusgen.memory.recall import build_memory_index, query_memory_index
from app.corpusgen.planner import plan_generation_tasks
from app.corpusgen.seeds import chunk_seed_documents, load_seed_documents
from app.corpusgen.specs import parse_corpus_spec


def fake_embedder(spec, texts):
    vectors = []
    for text in texts:
        vectors.append(
            [
                float(len(text)),
                float(sum(ord(ch) for ch in text) % 997),
                float(text.count("投射性") + text.count("预设") + 1),
            ]
        )
    return vectors


class TestCorpusMemory(unittest.TestCase):
    def test_memory_index_and_context_pack(self):
        payload = json.loads(Path("configs/corpusgen/domain/linguistics_zh_qa.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            payload["index_dir"] = tmp
            payload["output_dir"] = tmp
            payload["embedding_dimensions"] = 3
            spec = parse_corpus_spec(payload, source="memory-test")
            documents = load_seed_documents("configs/corpusgen/domain/linguistics_zh_seed.example.jsonl")
            chunks = chunk_seed_documents(documents, chunk_size=spec.seed_chunk_size, chunk_overlap=spec.seed_chunk_overlap)
            records = build_memory_records(spec, chunks)
            manifest = build_memory_index(spec, records, embedder=fake_embedder, force_rebuild=True)
            self.assertGreater(manifest["record_count"], 0)

            tasks = plan_generation_tasks(spec, records)
            hits = query_memory_index(spec, records, tasks[0].query, embedder=fake_embedder)
            pack = build_context_pack(spec, tasks[0], hits)

            self.assertTrue(pack["source_chunk_ids"])
            self.assertTrue(pack["evidence_pack"])
            self.assertTrue(pack["term_pack"])


if __name__ == "__main__":
    unittest.main()
