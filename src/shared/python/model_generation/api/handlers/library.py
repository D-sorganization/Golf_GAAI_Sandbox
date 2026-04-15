"""Library management endpoint handlers for ModelGenerationAPI."""

from __future__ import annotations

import tempfile
from pathlib import Path

from model_generation.api.models import APIRequest, APIResponse


class LibraryHandlersMixin:
    """Mixin providing model library endpoints."""

    def library_list_models(self, request: APIRequest) -> APIResponse:
        """List models in library."""
        if request is None:
            raise ValueError("request must be provided")
        from model_generation.library import ModelLibrary

        library = ModelLibrary()

        category = request.query_params.get("category")
        source = request.query_params.get("source")
        search = request.query_params.get("search")
        tags = (
            request.query_params.get("tags", "").split(",")
            if request.query_params.get("tags")
            else None
        )

        models = library.list_models(
            category=category,  # type: ignore[arg-type]
            source=source,  # type: ignore[arg-type]
            search=search,
            tags=tags,
        )

        return APIResponse.ok(
            {
                "count": len(models),
                "models": [
                    {
                        "id": m.id,
                        "name": m.name,
                        "category": m.category.value,
                        "source": m.source.value if m.source else None,
                        "tags": m.tags,
                        "description": m.description,
                    }
                    for m in models
                ],
            }
        )

    def library_get_model(self, request: APIRequest) -> APIResponse:
        """Get model details."""
        if request is None:
            raise ValueError("request must be provided")
        from model_generation.library import ModelLibrary

        model_id = request.query_params.get("model_id")
        if not model_id:
            return APIResponse.error("Missing model_id")

        library = ModelLibrary()
        models = library.list_models()

        for m in models:
            if m.name == model_id or getattr(m, "model_id", m.name) == model_id:  # type: ignore[attr-defined]
                return APIResponse.ok(
                    {
                        "id": getattr(m, "model_id", m.name),  # type: ignore[attr-defined]
                        "name": m.name,
                        "category": m.category.value,
                        "source": m.source.value if m.source else None,
                        "tags": m.tags,
                        "description": m.description,
                        "path": str(m.urdf_path) if m.urdf_path else None,
                    }
                )

        return APIResponse.not_found(f"Model not found: {model_id}")

    def library_add_model(self, request: APIRequest) -> APIResponse:
        """Add model to library."""
        if request is None:
            raise ValueError("request must be provided")
        from model_generation.library import ModelCategory, ModelLibrary

        body = request.body or {}

        content = body.get("content") or (
            request.files.get("file", b"").decode("utf-8") if request.files else None
        )

        if not content:
            return APIResponse.error("Missing URDF content")

        name = body.get("name", "unnamed")
        category_str = body.get("category", "other")
        tags = body.get("tags", [])

        try:
            category = ModelCategory(category_str)
        except ValueError:
            category = ModelCategory.OTHER

        library = ModelLibrary()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".urdf", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            entry = library.add_local_model(
                urdf_path=Path(temp_path),
                name=name,
                category=category,
                tags=tags,
            )

            if entry:
                return APIResponse.created(
                    {
                        "id": entry.model_id,
                        "name": entry.name,
                        "category": entry.category.value,
                    }
                )
            return APIResponse.error("Failed to add model")
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def library_remove_model(self, request: APIRequest) -> APIResponse:
        """Remove model from library."""
        if request is None:
            raise ValueError("request must be provided")
        from model_generation.library import ModelLibrary

        model_id = request.query_params.get("model_id")
        if not model_id:
            return APIResponse.error("Missing model_id")

        ModelLibrary()

        return APIResponse.error("Remove not implemented", 501)

    def library_download_model(self, request: APIRequest) -> APIResponse:
        """Download model URDF."""
        if request is None:
            raise ValueError("request must be provided")
        from model_generation.library import ModelLibrary

        model_id = request.query_params.get("model_id")
        if not model_id:
            return APIResponse.error("Missing model_id")

        library = ModelLibrary()
        model = library.load_model(model_id)

        if not model:
            return APIResponse.not_found(f"Model not found: {model_id}")

        urdf_string = model.to_urdf()

        return APIResponse.file(urdf_string, f"{model.name}.urdf")
