DATA_VERSION = "1.0"

REQUIRED_CONCEPT_FIELDS = {
    "name": str,
    "prompt": str,
    "examples": list,
    "category": str,
    "is_default": bool,
}

REQUIRED_EXAMPLE_FIELDS = {
    "text": str,
    "annotation": str,
}

OPTIONAL_EXAMPLE_FIELDS = {
    "explanation": str,
}
