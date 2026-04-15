"""
REST API for model_generation package.

Provides HTTP endpoints for URDF generation, conversion, editing, and library access.
Can be used with Flask, FastAPI, or other frameworks via adapters.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)

# Re-export models so existing imports from this module continue to work.
# Re-export adapters for the same backwards-compatibility reason.
from model_generation.api.adapters import FastAPIAdapter, FlaskAdapter  # noqa: E402
from model_generation.api.handlers import (  # noqa: E402
    ConversionHandlersMixin,
    CoreHandlersMixin,
    EditorHandlersMixin,
    GenerationHandlersMixin,
    InertiaHandlersMixin,
    LibraryHandlersMixin,
    ValidationHandlersMixin,
)
from model_generation.api.models import (  # noqa: E402
    APIRequest,
    APIResponse,
    HTTPMethod,
    Route,
)

__all__ = [
    "ModelGenerationAPI",
    "APIRequest",
    "APIResponse",
    "HTTPMethod",
    "Route",
    "FlaskAdapter",
    "FastAPIAdapter",
]


class ModelGenerationAPI(
    CoreHandlersMixin,
    GenerationHandlersMixin,
    ConversionHandlersMixin,
    ValidationHandlersMixin,
    InertiaHandlersMixin,
    LibraryHandlersMixin,
    EditorHandlersMixin,
):
    """
    REST API for model generation operations.

    Provides endpoints for:
    - URDF generation (parametric, humanoid)
    - Format conversion (SimScape, MJCF)
    - Model validation
    - Library operations
    - Inertia calculation

    Example with Flask:
        from flask import Flask, request, jsonify
        from model_generation.api import ModelGenerationAPI, FlaskAdapter

        app = Flask(__name__)
        api = ModelGenerationAPI()
        FlaskAdapter(api).register(app)

    Example with FastAPI:
        from fastapi import FastAPI
        from model_generation.api import ModelGenerationAPI, FastAPIAdapter

        app = FastAPI()
        api = ModelGenerationAPI()
        FastAPIAdapter(api).register(app)
    """

    def __init__(self, prefix: str = "/api/v1") -> None:
        """
        Initialize API.

        Args:
            prefix: URL prefix for all routes
        """
        if prefix is None:
            raise ValueError("prefix must be provided")
        self.prefix = prefix
        self._routes: list[Route] = []

        # Security configuration from environment
        self._api_key: str | None = os.environ.get("MODEL_GEN_API_KEY")
        self._cors_origins: str = os.environ.get("MODEL_GEN_CORS_ORIGINS", "")
        self._rate_limit: int | None = None
        rate_limit_str = os.environ.get("MODEL_GEN_RATE_LIMIT")
        if rate_limit_str:
            try:
                self._rate_limit = int(rate_limit_str)
            except ValueError:
                logger.warning("Invalid MODEL_GEN_RATE_LIMIT value: %s", rate_limit_str)

        self._is_production: bool = (
            os.environ.get("MODEL_GEN_ENV", "").lower() == "production"
        )

        # In-memory sliding window rate limiter: client_ip -> list[timestamp]
        self._rate_limit_windows: dict[str, list[float]] = {}

        self._register_routes()

    def _add_routes(
        self,
        routes: list[
            tuple[
                HTTPMethod,
                str,
                Callable[[APIRequest], APIResponse],
                str,
                list[str],
            ]
        ],
    ) -> None:
        """Register a batch of routes with shared metadata structure."""
        for method, path, handler, description, tags in routes:
            self.add_route(method, path, handler, description, tags)

    def _core_routes(
        self,
    ) -> list[
        tuple[HTTPMethod, str, Callable[[APIRequest], APIResponse], str, list[str]]
    ]:
        """Return the core API route definitions."""
        return (
            self._health_and_generation_routes()
            + self._conversion_and_validation_routes()
        )

    def _health_and_generation_routes(
        self,
    ) -> list[
        tuple[HTTPMethod, str, Callable[[APIRequest], APIResponse], str, list[str]]
    ]:
        """Return health and generation route definitions."""
        return [
            (HTTPMethod.GET, "/health", self.health_check, "Health check", []),
            (HTTPMethod.GET, "/info", self.get_api_info, "API information", []),
            (
                HTTPMethod.POST,
                "/generate/humanoid",
                self.generate_humanoid,
                "Generate humanoid URDF",
                ["generation"],
            ),
            (
                HTTPMethod.POST,
                "/generate/from-params",
                self.generate_from_params,
                "Generate URDF from parameters",
                ["generation"],
            ),
        ]

    def _conversion_and_validation_routes(
        self,
    ) -> list[
        tuple[HTTPMethod, str, Callable[[APIRequest], APIResponse], str, list[str]]
    ]:
        """Return conversion and validation route definitions."""
        return [
            (
                HTTPMethod.POST,
                "/convert/simscape-to-urdf",
                self.convert_simscape_to_urdf,
                "Convert SimScape to URDF",
                ["conversion"],
            ),
            (
                HTTPMethod.POST,
                "/convert/mjcf-to-urdf",
                self.convert_mjcf_to_urdf,
                "Convert MJCF to URDF",
                ["conversion"],
            ),
            (
                HTTPMethod.POST,
                "/convert/urdf-to-mjcf",
                self.convert_urdf_to_mjcf,
                "Convert URDF to MJCF",
                ["conversion"],
            ),
            (
                HTTPMethod.POST,
                "/validate",
                self.validate_urdf,
                "Validate URDF content",
                ["validation"],
            ),
            (
                HTTPMethod.POST,
                "/parse",
                self.parse_urdf,
                "Parse URDF and return structure",
                ["parsing"],
            ),
        ]

    def _inertia_and_library_routes(
        self,
    ) -> list[
        tuple[HTTPMethod, str, Callable[[APIRequest], APIResponse], str, list[str]]
    ]:
        """Return inertia and library route definitions."""
        return self._inertia_routes() + self._library_routes()

    def _inertia_routes(
        self,
    ) -> list[
        tuple[HTTPMethod, str, Callable[[APIRequest], APIResponse], str, list[str]]
    ]:
        """Return inertia route definitions."""
        return [
            (
                HTTPMethod.POST,
                "/inertia/calculate",
                self.calculate_inertia,
                "Calculate inertia for shape",
                ["inertia"],
            ),
            (
                HTTPMethod.POST,
                "/inertia/from-mesh",
                self.inertia_from_mesh,
                "Calculate inertia from mesh file",
                ["inertia"],
            ),
        ]

    def _library_routes(
        self,
    ) -> list[
        tuple[HTTPMethod, str, Callable[[APIRequest], APIResponse], str, list[str]]
    ]:
        """Return library route definitions."""
        return [
            (
                HTTPMethod.GET,
                "/library/models",
                self.library_list_models,
                "List available models",
                ["library"],
            ),
            (
                HTTPMethod.GET,
                "/library/models/{model_id}",
                self.library_get_model,
                "Get model details",
                ["library"],
            ),
            (
                HTTPMethod.POST,
                "/library/models",
                self.library_add_model,
                "Add model to library",
                ["library"],
            ),
            (
                HTTPMethod.DELETE,
                "/library/models/{model_id}",
                self.library_remove_model,
                "Remove model from library",
                ["library"],
            ),
            (
                HTTPMethod.GET,
                "/library/models/{model_id}/download",
                self.library_download_model,
                "Download model URDF",
                ["library"],
            ),
        ]

    def _register_core_routes(self) -> None:
        """Register health, generation, conversion, validation, and parsing routes."""
        self._add_routes(self._core_routes())

    def _register_inertia_and_library_routes(self) -> None:
        """Register inertia calculation and library management routes."""
        self._add_routes(self._inertia_and_library_routes())

    def _register_editor_routes(self) -> None:
        """Register editor-related routes."""
        self.add_route(
            HTTPMethod.POST,
            "/editor/compose",
            self.compose_models,
            "Compose model from multiple sources",
            ["editor"],
        )
        self.add_route(
            HTTPMethod.POST,
            "/editor/diff",
            self.diff_urdfs,
            "Compare two URDF files",
            ["editor"],
        )

    def _register_routes(self) -> None:
        """Register all API routes."""
        self._register_core_routes()
        self._register_inertia_and_library_routes()
        self._register_editor_routes()

    def add_route(
        self,
        method: HTTPMethod,
        path: str,
        handler: Callable[[APIRequest], APIResponse],
        description: str = "",
        tags: list[str] | None = None,
    ) -> None:
        """Add a route to the API."""
        self._routes.append(
            Route(
                method=method,
                path=self.prefix + path,
                handler=handler,
                description=description,
                tags=tags or [],
            )
        )

    def get_routes(self) -> list[Route]:
        """Get all registered routes."""
        return self._routes

    def _check_api_key(self, request: APIRequest) -> APIResponse | None:
        """Check API key authentication if MODEL_GEN_API_KEY is set.

        Returns None if auth passes, or a 401 APIResponse if auth fails.
        """
        if request is None:
            raise ValueError("request must be provided")
        if not self._api_key:
            return None
        provided_key = request.headers.get("X-API-Key")
        if not provided_key or provided_key != self._api_key:
            return APIResponse.error("Unauthorized: invalid or missing API key", 401)
        return None

    def _check_rate_limit(self, request: APIRequest) -> APIResponse | None:
        """Sliding window rate limiter.  Returns 429 if limit exceeded.

        Uses MODEL_GEN_RATE_LIMIT (requests per minute).  The client IP
        is extracted from the X-Forwarded-For header or defaults to
        "unknown".
        """
        if request is None:
            raise ValueError("request must be provided")
        if self._rate_limit is None:
            return None

        client_ip = (
            request.headers.get("X-Forwarded-For", "unknown").split(",")[0].strip()
        )
        now = time.time()
        window_start = now - 60.0

        timestamps = self._rate_limit_windows.setdefault(client_ip, [])
        self._rate_limit_windows[client_ip] = [
            ts for ts in timestamps if ts > window_start
        ]

        if len(self._rate_limit_windows[client_ip]) >= self._rate_limit:
            return APIResponse.error("Rate limit exceeded. Try again later.", 429)

        self._rate_limit_windows[client_ip].append(now)
        return None

    def _add_cors_headers(self, response: APIResponse) -> None:
        """Add CORS headers to response.

        The allowed origin is configured via the MODEL_GEN_CORS_ORIGINS
        environment variable (comma-separated list).  If not set, defaults
        to an empty string (no cross-origin access).
        """
        if response is None:
            raise ValueError("response must be provided")
        origin = self._cors_origins.split(",")[0].strip() if self._cors_origins else ""
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, PUT, DELETE, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-API-Key"

    def _add_security_headers(self, response: APIResponse) -> None:
        """Add security headers to response."""
        if response is None:
            raise ValueError("response must be provided")
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    def _finalize_response(self, response: APIResponse) -> APIResponse:
        """Attach standard headers before returning a response."""
        self._add_security_headers(response)
        self._add_cors_headers(response)
        return response

    def _process_security_prechecks(self, request: APIRequest) -> APIResponse | None:
        """Run authentication and rate-limit checks."""
        auth_error = self._check_api_key(request)
        if auth_error is not None:
            return self._finalize_response(auth_error)

        rate_error = self._check_rate_limit(request)
        if rate_error is not None:
            return self._finalize_response(rate_error)
        return None

    def _match_route(self, route: Route, request: APIRequest) -> bool:
        """Match a route against a request path and collect path params."""
        route_parts = route.path.split("/")
        request_parts = request.path.split("/")
        if len(route_parts) != len(request_parts):
            return False

        params: dict[str, str] = {}
        for route_part, request_part in zip(route_parts, request_parts, strict=False):
            if route_part.startswith("{") and route_part.endswith("}"):
                params[route_part[1:-1]] = request_part
                continue
            if route_part != request_part:
                return False

        request.query_params.update(params)
        return True

    def handle_request(self, request: APIRequest) -> APIResponse:
        """Handle an API request."""
        if request is None:
            raise ValueError("request must be provided")
        precheck_error = self._process_security_prechecks(request)
        if precheck_error is not None:
            return precheck_error

        for route in self._routes:
            if route.method != request.method or not self._match_route(route, request):
                continue

            try:
                response = route.handler(request)
            except (ValueError, TypeError, KeyError, RuntimeError, OSError) as exc:
                logger.exception("Error handling request")
                response = APIResponse.error(str(exc), 500)
            return self._finalize_response(response)

        return self._finalize_response(
            APIResponse.not_found(f"No route for {request.method.value} {request.path}")
        )
