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

    def register(self, app: Any) -> None:
        """Register routes with Flask app."""
        from flask import jsonify, make_response
        from flask import request as flask_request

        for route in self.api.get_routes():
            endpoint = route.path.replace("/", "_").replace("{", "").replace("}", "")

            def make_handler(r: Route) -> Callable[..., Any]:
                def handler(**kwargs: Any) -> Any:
                    api_request = APIRequest(
                        method=HTTPMethod(flask_request.method),
                        path=flask_request.path,
                        query_params={**flask_request.args, **kwargs},
                        body=flask_request.get_json(silent=True),
                        files={k: v.read() for k, v in flask_request.files.items()},
                        headers=dict(flask_request.headers),
                    )

                    response = self.api.handle_request(api_request)

                    if isinstance(response.body, bytes):
                        flask_response = make_response(response.body)
                    elif isinstance(response.body, dict):
                        flask_response = make_response(jsonify(response.body))
                    else:
                        flask_response = make_response(response.body)

                    flask_response.status_code = response.status_code
                    flask_response.content_type = response.content_type

                    for k, v in response.headers.items():
                        flask_response.headers[k] = v

                    return flask_response

                return handler

            flask_path = route.path.replace("{", "<").replace("}", ">")
            app.add_url_rule(
                flask_path,
                endpoint=endpoint,
                view_func=make_handler(route),
                methods=[route.method.value],
            )


class FastAPIAdapter:
    """Adapter for FastAPI framework."""

    def __init__(self, api: ModelGenerationAPI) -> None:
        if not (api is not None):
            raise ValueError("api must be provided")
        self.api = api

    def register(self, app: Any) -> None:
        """Register routes with FastAPI app."""
        from fastapi import Request, Response
        from fastapi.responses import JSONResponse

        for route in self.api.get_routes():

            async def make_handler(r: Route) -> Callable[..., Any]:
                async def handler(request: Request, **kwargs: Any) -> Any:
                    body = None
                    try:
                        body = await request.json()
                    except (ValueError, UnicodeDecodeError) as e:
                        logger.debug("Failed to parse request JSON body: %s", e)

                    files = {}
                    form = await request.form()
                    for key, value in form.items():
                        if hasattr(value, "read"):
                            files[key] = await value.read()

                    api_request = APIRequest(
                        method=HTTPMethod(request.method),
                        path=request.url.path,
                        query_params={**request.query_params, **kwargs},
                        body=body,
                        files=files,
                        headers=dict(request.headers),
                    )

                    response = self.api.handle_request(api_request)

                    if isinstance(response.body, bytes):
                        return Response(
                            content=response.body,
                            status_code=response.status_code,
                            media_type=response.content_type,
                            headers=response.headers,
                        )
                    return JSONResponse(
                        content=response.body,
                        status_code=response.status_code,
                        headers=response.headers,
                    )

                return handler

            app.add_api_route(
                route.path,
                make_handler(route),
                methods=[route.method.value],
                tags=route.tags,
                summary=route.description,
            )
