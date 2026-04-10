"""Framework adapters for ModelGenerationAPI."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from model_generation.api.models import APIRequest, HTTPMethod, Route

if TYPE_CHECKING:
    from model_generation.api.rest_api import ModelGenerationAPI

logger = logging.getLogger(__name__)


class FlaskAdapter:
    """Adapter for Flask framework."""

    def __init__(self, api: ModelGenerationAPI) -> None:
        if not (api is not None):
            raise ValueError("api must be provided")
        self.api = api

    def _build_request(self, flask_request: Any, kwargs: dict[str, Any]) -> APIRequest:
        """Build an APIRequest from a Flask request object."""
        return APIRequest(
            method=HTTPMethod(flask_request.method),
            path=flask_request.path,
            query_params={**flask_request.args, **kwargs},
            body=flask_request.get_json(silent=True),
            files={k: v.read() for k, v in flask_request.files.items()},
            headers=dict(flask_request.headers),
        )

    def _build_response(
        self,
        response: Any,
        jsonify: Callable[..., Any],
        make_response: Callable[..., Any],
    ) -> Any:
        """Convert an APIResponse into a Flask response."""
        if isinstance(response.body, bytes):
            flask_response = make_response(response.body)
        elif isinstance(response.body, dict):
            flask_response = make_response(jsonify(response.body))
        else:
            flask_response = make_response(response.body)

        flask_response.status_code = response.status_code
        flask_response.content_type = response.content_type
        for key, value in response.headers.items():
            flask_response.headers[key] = value
        return flask_response

    def _make_handler(
        self,
        route: Route,
        flask_request: Any,
        jsonify: Callable[..., Any],
        make_response: Callable[..., Any],
    ) -> Callable[..., Any]:
        """Create a Flask route handler."""

        def handler(**kwargs: Any) -> Any:
            api_request = self._build_request(flask_request, kwargs)
            response = self.api.handle_request(api_request)
            return self._build_response(response, jsonify, make_response)

        return handler

    def register(self, app: Any) -> None:
        """Register routes with Flask app."""
        from flask import jsonify, make_response
        from flask import request as flask_request

        for route in self.api.get_routes():
            endpoint = route.path.replace("/", "_").replace("{", "").replace("}", "")

            flask_path = route.path.replace("{", "<").replace("}", ">")
            app.add_url_rule(
                flask_path,
                endpoint=endpoint,
                view_func=self._make_handler(
                    route,
                    flask_request,
                    jsonify,
                    make_response,
                ),
                methods=[route.method.value],
            )


class FastAPIAdapter:
    """Adapter for FastAPI framework."""

    def __init__(self, api: ModelGenerationAPI) -> None:
        if not (api is not None):
            raise ValueError("api must be provided")
        self.api = api

    async def _parse_json_body(self, request: Any) -> Any:
        """Parse an optional JSON request body."""
        try:
            return await request.json()
        except (ValueError, UnicodeDecodeError) as exc:
            logger.debug("Failed to parse request JSON body: %s", exc)
            return None

    async def _parse_uploads(self, request: Any) -> dict[str, bytes]:
        """Read uploaded file bodies from a FastAPI request."""
        files: dict[str, bytes] = {}
        form = await request.form()
        for key, value in form.items():
            if hasattr(value, "read"):
                files[key] = await value.read()
        return files

    async def _build_request(self, request: Any, kwargs: dict[str, Any]) -> APIRequest:
        """Build an APIRequest from a FastAPI request object."""
        return APIRequest(
            method=HTTPMethod(request.method),
            path=request.url.path,
            query_params={**request.query_params, **kwargs},
            body=await self._parse_json_body(request),
            files=await self._parse_uploads(request),
            headers=dict(request.headers),
        )

    def _build_response(
        self,
        response: Any,
        json_response: Any,
        response_cls: Any,
    ) -> Any:
        """Convert an APIResponse into a FastAPI response."""
        if isinstance(response.body, bytes):
            return response_cls(
                content=response.body,
                status_code=response.status_code,
                media_type=response.content_type,
                headers=response.headers,
            )
        return json_response(
            content=response.body,
            status_code=response.status_code,
            headers=response.headers,
        )

    def _make_handler(
        self,
        route: Route,
        json_response: Any,
        response_cls: Any,
    ) -> Callable[..., Any]:
        """Create a FastAPI route handler."""

        async def handler(request: Any, **kwargs: Any) -> Any:
            api_request = await self._build_request(request, kwargs)
            response = self.api.handle_request(api_request)
            return self._build_response(response, json_response, response_cls)

        return handler

    def register(self, app: Any) -> None:
        """Register routes with FastAPI app."""
        from fastapi import Response
        from fastapi.responses import JSONResponse

        for route in self.api.get_routes():
            app.add_api_route(
                route.path,
                self._make_handler(route, JSONResponse, Response),
                methods=[route.method.value],
                tags=route.tags,
                summary=route.description,
            )
