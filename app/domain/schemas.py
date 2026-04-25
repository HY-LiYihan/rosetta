DATA_VERSION = "3.0"

REQUIRED_CONCEPT_FIELDS = {
    "name": str,
    "prompt": str,
    "examples": list,
    "category": str,
    "is_default": bool,
}

REQUIRED_EXAMPLE_FIELDS = {
    "text": str,
    "annotation": object,  # str (legacy) or dict (AnnotationDoc) — validated separately
    "explanation": str,
}
