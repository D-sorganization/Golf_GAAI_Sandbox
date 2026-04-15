"""Validation and parsing endpoint handlers for ModelGenerationAPI."""

from __future__ import annotations

from model_generation.api.models import APIRequest, APIResponse


class ValidationHandlersMixin:
    """Mixin providing URDF validation and parsing endpoints."""

    def validate_urdf(self, request: APIRequest) -> APIResponse:
        """Validate URDF content."""
        if request is None:
            raise ValueError("request must be provided")
        from model_generation.editor.text_editor import (
            URDFTextEditor,
            ValidationSeverity,
        )

        body = request.body or {}

        content = body.get("content") or (
            request.files.get("file", b"").decode("utf-8") if request.files else None
        )

        if not content:
            return APIResponse.error("Missing URDF content")

        editor = URDFTextEditor()
        editor.load_string(content)

        messages = editor.validate()

        has_errors = any(m.severity == ValidationSeverity.ERROR for m in messages)

        return APIResponse.ok(
            {
                "valid": not has_errors,
                "error_count": sum(
                    1 for m in messages if m.severity == ValidationSeverity.ERROR
                ),
                "warning_count": sum(
                    1 for m in messages if m.severity == ValidationSeverity.WARNING
                ),
                "messages": [
                    {
                        "severity": m.severity.value,
                        "line": m.line,
                        "column": m.column,
                        "message": m.message,
                        "element": m.element,
                    }
                    for m in messages
                ],
            }
        )

    def parse_urdf(self, request: APIRequest) -> APIResponse:
        """Parse URDF and return structure."""
        if request is None:
            raise ValueError("request must be provided")
        from model_generation.converters.urdf_parser import URDFParser

        body = request.body or {}

        content = body.get("content") or (
            request.files.get("file", b"").decode("utf-8") if request.files else None
        )

        if not content:
            return APIResponse.error("Missing URDF content")

        parser = URDFParser()

        try:
            model = parser.parse(content)
        except (ValueError, KeyError, OSError) as e:
            return APIResponse.error(f"Parse failed: {e}", 422)

        root = model.get_root_link()

        return APIResponse.ok(
            {
                "name": model.name,
                "root_link": root.name if root else None,
                "links": [link.to_dict() for link in model.links],
                "joints": [j.to_dict() for j in model.joints],
                "materials": {k: v.to_dict() for k, v in model.materials.items()},
                "warnings": model.warnings,
            }
        )
