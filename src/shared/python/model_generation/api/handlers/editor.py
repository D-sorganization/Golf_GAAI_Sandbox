"""Editor endpoint handlers for ModelGenerationAPI."""

from __future__ import annotations

from typing import Any

from model_generation.api.models import APIRequest, APIResponse


class EditorHandlersMixin:
    """Mixin providing URDF editor endpoints."""

    def _load_sources(
        self,
        editor: Any,
        sources: dict[str, str],
    ) -> APIResponse | None:
        """Load source models into the editor."""
        for model_id, content in sources.items():
            try:
                editor.load_model(model_id, content, read_only=True)
            except (ValueError, KeyError, OSError) as exc:
                return APIResponse.error(f"Failed to load model '{model_id}': {exc}")
        return None

    def _apply_operations(
        self,
        editor: Any,
        operations: list[dict[str, str]],
    ) -> None:
        """Apply composition operations to the output model."""
        for operation in operations:
            operation_type = operation.get("type")
            if operation_type == "copy_subtree":
                editor.copy_subtree(operation["source"], operation["link"])
            elif operation_type == "paste":
                editor.paste(
                    "output",
                    attach_to=operation.get("attach_to"),
                    prefix=operation.get("prefix", ""),
                )
            elif operation_type == "delete_subtree":
                editor.delete_subtree("output", operation["link"])
            elif operation_type == "rename":
                editor.rename_link(
                    "output", operation["old_name"], operation["new_name"]
                )

    def _build_compose_response(
        self,
        request: APIRequest,
        output_name: str,
        urdf_string: str,
        stats: dict[str, int],
    ) -> APIResponse:
        """Build the successful compose response."""
        if request.query_params.get("download") == "true":
            return APIResponse.file(urdf_string, f"{output_name}.urdf")
        return APIResponse.ok(
            {
                "name": output_name,
                "links": stats.get("link_count", 0),
                "joints": stats.get("joint_count", 0),
                "urdf": urdf_string,
            }
        )

    def compose_models(self, request: APIRequest) -> APIResponse:
        """Compose model from multiple sources."""
        if request is None:
            raise ValueError("request must be provided")
        from model_generation.editor import FrankensteinEditor

        body = request.body or {}

        sources = body.get("sources", {})
        operations = body.get("operations", [])
        output_name = str(body.get("name", "composed_robot"))

        if not sources:
            return APIResponse.error("Missing 'sources' in request body")

        editor = FrankensteinEditor()
        load_error = self._load_sources(editor, sources)
        if load_error is not None:
            return load_error
        editor.create_model("output", output_name)
        self._apply_operations(editor, operations)
        urdf_string = editor.export_model("output")
        stats = editor.get_model_statistics("output")
        return self._build_compose_response(request, output_name, urdf_string, stats)

    def diff_urdfs(self, request: APIRequest) -> APIResponse:
        """Compare two URDF files."""
        if request is None:
            raise ValueError("request must be provided")
        from model_generation.editor.text_editor import URDFTextEditor

        body = request.body or {}

        content_a = body.get("content_a")
        content_b = body.get("content_b")

        if not content_a or not content_b:
            return APIResponse.error("Missing content_a or content_b")

        editor = URDFTextEditor()
        editor.load_string(content_a)

        diff_result = editor.get_diff_with_string(content_b)

        return APIResponse.ok(
            {
                "has_changes": diff_result.has_changes,
                "additions": diff_result.additions,
                "deletions": diff_result.deletions,
                "hunks": len(diff_result.hunks),
                "unified_diff": diff_result.unified_diff,
            }
        )
