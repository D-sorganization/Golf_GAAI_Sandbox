"""Editor endpoint handlers for ModelGenerationAPI."""

from __future__ import annotations

from model_generation.api.models import APIRequest, APIResponse


class EditorHandlersMixin:
    """Mixin providing URDF editor endpoints."""

    def compose_models(self, request: APIRequest) -> APIResponse:
        """Compose model from multiple sources."""
        if not (request is not None):
            raise ValueError("request must be provided")
        from model_generation.editor import FrankensteinEditor

        body = request.body or {}

        sources = body.get("sources", {})
        operations = body.get("operations", [])
        output_name = body.get("name", "composed_robot")

        if not sources:
            return APIResponse.error("Missing 'sources' in request body")

        editor = FrankensteinEditor()

        for model_id, content in sources.items():
            try:
                editor.load_model(model_id, content, read_only=True)
            except (ValueError, KeyError, OSError) as e:
                return APIResponse.error(f"Failed to load model '{model_id}': {e}")

        editor.create_model("output", output_name)

        for op in operations:
            op_type = op.get("type")

            if op_type == "copy_subtree":
                editor.copy_subtree(op["source"], op["link"])
            elif op_type == "paste":
                editor.paste(
                    "output",
                    attach_to=op.get("attach_to"),
                    prefix=op.get("prefix", ""),
                )
            elif op_type == "delete_subtree":
                editor.delete_subtree("output", op["link"])
            elif op_type == "rename":
                editor.rename_link("output", op["old_name"], op["new_name"])

        urdf_string = editor.export_model("output")
        stats = editor.get_model_statistics("output")

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

    def diff_urdfs(self, request: APIRequest) -> APIResponse:
        """Compare two URDF files."""
        if not (request is not None):
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
