import ast
import json
import re
import tempfile
import unittest
from pathlib import Path

from app.corpusgen.runner import build_memory_bank, generate_corpus, plan_corpus, prepare_seed_corpus


def fake_embedder(spec, texts):
    vectors = []
    for text in texts:
        vectors.append(
            [
                float(len(text)),
                float(sum(ord(ch) for ch in text) % 991),
                float(text.count("投射性") + text.count("预设") + text.count("焦点") + 1),
            ]
        )
    return vectors


def fake_predictor(spec, prompt):
    focus_match = re.search(r"聚焦主题：(.*)", prompt)
    focus = focus_match.group(1).strip() if focus_match else "概念"
    source_match = re.search(r"这个集合中选择：(\[[^\n]+\])", prompt)
    source_chunk_ids = ast.literal_eval(source_match.group(1)) if source_match else ["chunk-001"]
    payload = {
        "items": [
            {
                "question": f"{focus}在语言学分析中通常如何判断？",
                "answer": (
                    f"{focus}需要结合证据包中的术语、判据与嵌入稳定性线索来判断，"
                    "同时说明它与近邻概念之间的边界，并给出能够复核的分析理由。"
                ),
                "rationale": "基于压缩证据包生成。",
                "source_chunk_ids": source_chunk_ids[:1],
            }
        ]
    }
    return json.dumps(payload, ensure_ascii=False)


class TestCorpusgenRunner(unittest.TestCase):
    def test_end_to_end_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec_payload = json.loads(Path("configs/corpusgen/domain/linguistics_zh_qa.json").read_text(encoding="utf-8"))
            spec_payload["output_dir"] = tmp
            spec_payload["index_dir"] = f"{tmp}/indexes"
            spec_payload["embedding_dimensions"] = 3
            spec_path = Path(tmp) / "spec.json"
            spec_path.write_text(json.dumps(spec_payload, ensure_ascii=False, indent=2), encoding="utf-8")

            prepare_manifest = prepare_seed_corpus(
                spec_path=spec_path,
                dataset_path="configs/corpusgen/domain/linguistics_zh_seed.example.jsonl",
                output_dir=tmp,
            )
            memory_manifest = build_memory_bank(
                spec_path=spec_path,
                chunks_path=Path(prepare_manifest["output_dir"]) / "seed_chunks.jsonl",
                output_dir=tmp,
                embedder=fake_embedder,
                force_rebuild=True,
            )
            plan_manifest = plan_corpus(
                spec_path=spec_path,
                memory_path=memory_manifest["memory_records_path"],
                output_dir=tmp,
            )
            generate_manifest = generate_corpus(
                spec_path=spec_path,
                memory_path=memory_manifest["memory_records_path"],
                plan_path=plan_manifest["tasks_path"],
                output_dir=tmp,
                limit_tasks=1,
                predictor=fake_predictor,
                embedder=fake_embedder,
            )

            accepted_path = Path(generate_manifest["output_dir"]) / "accepted.jsonl"
            accepted_rows = accepted_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(generate_manifest["accepted_count"], 1)
            self.assertEqual(len(accepted_rows), 1)
            row = json.loads(accepted_rows[0])
            self.assertEqual(row["schema"], "qa")
            self.assertIn("lineage", row)
            self.assertTrue(row["source_chunk_ids"])


if __name__ == "__main__":
    unittest.main()
