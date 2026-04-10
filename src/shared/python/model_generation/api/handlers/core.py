"""Core/system endpoint handlers for ModelGenerationAPI."""

from __future__ import annotations

from typing import Any

from model_generation.api.models import APIRequest, APIResponse


class CoreHandlersMixin:
    """Mixin providing health and API-info endpoints."""

    _routes: Any  # provided by ModelGenerationAPI

    def health_check(self, request: APIRequest) -> APIResponse:
        """Health check endpoint."""
        return APIResponse.ok({"status": "healthy", "service": "model_generation"})

    def get_api_info(self, request: APIRequest) -> APIResponse:
        """Get API information."""
        return APIResponse.ok(
            {
                "name": "Model Generation API",
                "version": "1.0.0",
                "description": "REST API for URDF generation, conversion, and manipulation",
                "endpoints": [
                    {
                        "method": r.method.value,
                        "path": r.path,
                        "description": r.description,
                        "tags": r.tags,
                    }
                    for r in self._routes
                ],
            }
        )
