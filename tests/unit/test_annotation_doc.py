import unittest

from app.domain.annotation_doc import (
    ANNOTATION_DOC_VERSION,
    legacy_string_to_spans,
    make_annotation_doc,
    spans_to_legacy_string,
    validate_annotation_doc,
)


class TestLegacyStringToSpans(unittest.TestCase):
    def test_single_explicit_span(self):
        spans = legacy_string_to_spans("他买了苹果", "[苹果]{名词}")
        self.assertEqual(len(spans), 1)
        s = spans[0]
        self.assertEqual(s["id"], "s0")
        self.assertEqual(s["text"], "苹果")
        self.assertEqual(s["label"], "名词")
        self.assertFalse(s["implicit"])
        self.assertEqual(s["start"], 3)
        self.assertEqual(s["end"], 5)

    def test_multiple_spans_ordered_search(self):
        spans = legacy_string_to_spans("AB BA", "[A]{X} [B]{Y}")
        self.assertEqual(spans[0]["start"], 0)
        self.assertEqual(spans[1]["start"], 1)

    def test_implicit_span_no_offset(self):
        spans = legacy_string_to_spans("今天天气很好", "[!好]{形容词}")
        self.assertEqual(spans[0]["start"], -1)
        self.assertEqual(spans[0]["end"], -1)
        self.assertTrue(spans[0]["implicit"])
        self.assertEqual(spans[0]["text"], "好")

    def test_text_not_found_in_source(self):
        spans = legacy_string_to_spans("hello", "[world]{N}")
        self.assertEqual(spans[0]["start"], -1)
        self.assertEqual(spans[0]["end"], -1)

    def test_repeated_word_sequential(self):
        spans = legacy_string_to_spans("AAA", "[A]{X} [A]{Y}")
        self.assertEqual(spans[0]["start"], 0)
        self.assertEqual(spans[1]["start"], 1)


class TestValidateAnnotationDoc(unittest.TestCase):
    def _valid_doc(self):
        return {
            "version": ANNOTATION_DOC_VERSION,
            "text": "示例文本",
            "layers": {
                "spans": [{"id": "s0", "start": 0, "end": 2, "text": "示例", "label": "X", "implicit": False}],
                "relations": [],
                "attributes": [],
                "comments": [],
                "document_labels": [],
            },
            "provenance": {},
            "meta": {},
        }

    def test_valid_doc(self):
        ok, reason = validate_annotation_doc(self._valid_doc())
        self.assertTrue(ok)
        self.assertIsNone(reason)

    def test_not_a_dict(self):
        ok, reason = validate_annotation_doc("string")
        self.assertFalse(ok)

    def test_missing_version(self):
        doc = self._valid_doc()
        del doc["version"]
        ok, reason = validate_annotation_doc(doc)
        self.assertFalse(ok)

    def test_spans_not_list(self):
        doc = self._valid_doc()
        doc["layers"]["spans"] = {}
        ok, reason = validate_annotation_doc(doc)
        self.assertFalse(ok)

    def test_span_missing_field(self):
        doc = self._valid_doc()
        del doc["layers"]["spans"][0]["label"]
        ok, reason = validate_annotation_doc(doc)
        self.assertFalse(ok)


class TestSpansToLegacyString(unittest.TestCase):
    def test_explicit(self):
        spans = [{"id": "s0", "start": 0, "end": 2, "text": "示例", "label": "X", "implicit": False}]
        self.assertEqual(spans_to_legacy_string(spans), "[示例]{X}")

    def test_implicit(self):
        spans = [{"id": "s0", "start": -1, "end": -1, "text": "含义", "label": "Y", "implicit": True}]
        self.assertEqual(spans_to_legacy_string(spans), "[!含义]{Y}")

    def test_round_trip(self):
        source = "他买了苹果"
        annotation_str = "[苹果]{名词}"
        spans = legacy_string_to_spans(source, annotation_str)
        result = spans_to_legacy_string(spans)
        self.assertEqual(result, "[苹果]{名词}")


class TestMakeAnnotationDoc(unittest.TestCase):
    def test_structure(self):
        doc = make_annotation_doc("苹果很好吃", "[苹果]{名词}")
        self.assertEqual(doc["version"], ANNOTATION_DOC_VERSION)
        self.assertEqual(doc["text"], "苹果很好吃")
        self.assertIn("spans", doc["layers"])
        self.assertIn("relations", doc["layers"])
        self.assertIn("attributes", doc["layers"])
        self.assertIn("comments", doc["layers"])
        self.assertIn("document_labels", doc["layers"])
        self.assertIn("provenance", doc)
        self.assertEqual(doc["layers"]["spans"][0]["label"], "名词")

    def test_meta_defaults_empty(self):
        doc = make_annotation_doc("text", "[text]{N}")
        self.assertEqual(doc["meta"], {})

    def test_custom_meta(self):
        doc = make_annotation_doc("text", "[text]{N}", meta={"model": "glm-4"})
        self.assertEqual(doc["meta"]["model"], "glm-4")


if __name__ == "__main__":
    unittest.main()
