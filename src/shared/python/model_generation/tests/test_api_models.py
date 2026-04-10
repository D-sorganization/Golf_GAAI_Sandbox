"""Tests for api/models.py — the extracted REST API data models."""

from __future__ import annotations

from model_generation.api.models import (
    APIRequest,
    APIResponse,
    HTTPMethod,
    Route,
)


class TestHTTPMethod:
    def test_all_methods_defined(self):
        assert HTTPMethod.GET.value == "GET"
        assert HTTPMethod.POST.value == "POST"
        assert HTTPMethod.PUT.value == "PUT"
        assert HTTPMethod.DELETE.value == "DELETE"
        assert HTTPMethod.PATCH.value == "PATCH"


class TestAPIRequest:
    def test_minimal_construction(self):
        req = APIRequest(method=HTTPMethod.GET, path="/health")
        assert req.method == HTTPMethod.GET
        assert req.path == "/health"
        assert req.query_params == {}
        assert req.body is None
        assert req.files == {}
        assert req.headers == {}

    def test_full_construction(self):
        req = APIRequest(
            method=HTTPMethod.POST,
            path="/generate",
            query_params={"download": "true"},
            body={"name": "robot"},
            files={"file": b"data"},
            headers={"X-API-Key": "secret"},
        )
        assert req.query_params["download"] == "true"
        assert req.body["name"] == "robot"
        assert req.files["file"] == b"data"
        assert req.headers["X-API-Key"] == "secret"


class TestAPIResponse:
    def test_ok_factory(self):
        r = APIResponse.ok({"status": "healthy"})
        assert r.status_code == 200
        assert r.body["status"] == "healthy"
        assert r.content_type == "application/json"

    def test_created_factory(self):
        r = APIResponse.created({"id": "abc"})
        assert r.status_code == 201
        assert r.body["id"] == "abc"

    def test_error_factory_default_status(self):
        r = APIResponse.error("bad input")
        assert r.status_code == 400
        assert "error" in r.body

    def test_error_factory_custom_status(self):
        r = APIResponse.error("server error", 500)
        assert r.status_code == 500

    def test_not_found_factory(self):
        r = APIResponse.not_found("missing resource")
        assert r.status_code == 404
        assert "error" in r.body

    def test_file_factory_string(self):
        r = APIResponse.file("<robot/>", "robot.urdf")
        assert r.status_code == 200
        assert isinstance(r.body, bytes)
        assert r.body == b"<robot/>"
        assert "Content-Disposition" in r.headers
        assert "robot.urdf" in r.headers["Content-Disposition"]

    def test_file_factory_bytes(self):
        r = APIResponse.file(b"<robot/>", "robot.urdf")
        assert r.body == b"<robot/>"

    def test_file_factory_custom_content_type(self):
        r = APIResponse.file("<mujoco/>", "model.xml", "application/xml")
        assert r.content_type == "application/xml"

    def test_headers_default_empty(self):
        r = APIResponse.ok({})
        assert r.headers == {}


class TestRoute:
    def test_construction(self):
        def dummy(req: APIRequest) -> APIResponse:
            return APIResponse.ok({})

        route = Route(
            method=HTTPMethod.GET,
            path="/api/v1/health",
            handler=dummy,
            description="Health check",
            tags=["core"],
        )
        assert route.method == HTTPMethod.GET
        assert route.path == "/api/v1/health"
        assert route.handler is dummy
        assert route.description == "Health check"
        assert route.tags == ["core"]

    def test_defaults(self):
        def dummy(req: APIRequest) -> APIResponse:
            return APIResponse.ok({})

        route = Route(method=HTTPMethod.POST, path="/foo", handler=dummy)
        assert route.description == ""
        assert route.tags == []


class TestModelsBackwardsCompatibility:
    """Verify that importing via rest_api still works (backwards compat)."""

    def test_import_via_rest_api(self):
        from model_generation.api.rest_api import (
            APIRequest,
            APIResponse,
            HTTPMethod,
            Route,
        )

        r = APIResponse.ok({"ok": True})
        assert r.status_code == 200
        req = APIRequest(method=HTTPMethod.GET, path="/")
        assert req.path == "/"
        assert Route is not None

    def test_import_via_api_package(self):
        from model_generation.api import APIRequest, APIResponse, HTTPMethod, Route

        r = APIResponse.error("oops")
        assert r.status_code == 400
        req = APIRequest(method=HTTPMethod.POST, path="/x")
        assert req.method == HTTPMethod.POST
        assert Route is not None
