from __future__ import annotations

from dataclasses import asdict, dataclass

from app.domain.annotation_format import extract_annotation_tokens, validate_annotation_markup
from app.research.contracts import ConflictRule


@dataclass(frozen=True)
class VerificationIssue:
    code: str
    severity: str
    message: str


def issue_to_dict(issue: VerificationIssue) -> dict:
    return asdict(issue)


def verify_annotation_result(
    sample_text: str,
    parsed_result: dict | None,
    conflict_rules: tuple[ConflictRule, ...],
) -> list[VerificationIssue]:
    issues: list[VerificationIssue] = []
    if parsed_result is None:
        return [VerificationIssue(code="invalid_json", severity="error", message="模型输出无法解析为合法 JSON 标注结果")]

    if parsed_result.get("text") != sample_text:
        issues.append(
            VerificationIssue(
                code="text_mismatch",
                severity="warning",
                message="返回结果中的 text 与输入文本不一致，建议人工复核",
            )
        )

    annotation = parsed_result.get("annotation", "")
    ok, reason = validate_annotation_markup(annotation)
    if not ok:
        issues.append(
            VerificationIssue(
                code="invalid_annotation",
                severity="error",
                message=f"annotation 不符合格式规范: {reason}",
            )
        )
        return issues

    labels: set[str] = set()
    for token in extract_annotation_tokens(annotation):
        labels.add(token["label"])
        if not token["implicit"] and token["text"] not in sample_text:
            issues.append(
                VerificationIssue(
                    code="span_not_found",
                    severity="error",
                    message=f"显性标注片段 `{token['text']}` 未在原文中找到",
                )
            )

    if not isinstance(parsed_result.get("explanation"), str) or not parsed_result["explanation"].strip():
        issues.append(
            VerificationIssue(
                code="missing_explanation",
                severity="error",
                message="explanation 不能为空",
            )
        )

    for rule in conflict_rules:
        if set(rule.labels).issubset(labels):
            issues.append(
                VerificationIssue(
                    code="logic_conflict",
                    severity="error",
                    message=f"{rule.name}: {rule.message}",
                )
            )

    return issues
