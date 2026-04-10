"""Tests for the decomposed handler mixin modules."""

from __future__ import annotations

from model_generation.api.handlers import (
    ConversionHandlersMixin,
    CoreHandlersMixin,
    EditorHandlersMixin,
    GenerationHandlersMixin,
    InertiaHandlersMixin,
    LibraryHandlersMixin,
    ValidationHandlersMixin,
)
from model_generation.api.models import APIRequest, HTTPMethod
from model_generation.api.rest_api import ModelGenerationAPI


class TestHandlerMixinsExposed:
    """Each mixin must expose the correct public methods."""

    def test_core_mixin_methods(self):
        assert callable(CoreHandlersMixin.health_check)
        assert callable(CoreHandlersMixin.get_api_info)

    def test_generation_mixin_methods(self):
        assert callable(GenerationHandlersMixin.generate_humanoid)
        assert callable(GenerationHandlersMixin.generate_from_params)

    def test_conversion_mixin_methods(self):
        assert callable(ConversionHandlersMixin.convert_simscape_to_urdf)
        assert callable(ConversionHandlersMixin.convert_mjcf_to_urdf)
        assert callable(ConversionHandlersMixin.convert_urdf_to_mjcf)

    def test_validation_mixin_methods(self):
        assert callable(ValidationHandlersMixin.validate_urdf)
        assert callable(ValidationHandlersMixin.parse_urdf)

    def test_inertia_mixin_methods(self):
        assert callable(InertiaHandlersMixin.calculate_inertia)
        assert callable(InertiaHandlersMixin.inertia_from_mesh)

    def test_library_mixin_methods(self):
        assert callable(LibraryHandlersMixin.library_list_models)
        assert callable(LibraryHandlersMixin.library_get_model)
        assert callable(LibraryHandlersMixin.library_add_model)
        assert callable(LibraryHandlersMixin.library_remove_model)
        assert callable(LibraryHandlersMixin.library_download_model)

    def test_editor_mixin_methods(self):
        assert callable(EditorHandlersMixin.compose_models)
        assert callable(EditorHandlersMixin.diff_urdfs)


class TestModelGenerationAPIInheritsAllMixins:
    """ModelGenerationAPI must inherit from every handler mixin."""

    def test_inherits_core(self):
        assert issubclass(ModelGenerationAPI, CoreHandlersMixin)

    def test_inherits_generation(self):
        assert issubclass(ModelGenerationAPI, GenerationHandlersMixin)

    def test_inherits_conversion(self):
        assert issubclass(ModelGenerationAPI, ConversionHandlersMixin)

    def test_inherits_validation(self):
        assert issubclass(ModelGenerationAPI, ValidationHandlersMixin)

    def test_inherits_inertia(self):
        assert issubclass(ModelGenerationAPI, InertiaHandlersMixin)

    def test_inherits_library(self):
        assert issubclass(ModelGenerationAPI, LibraryHandlersMixin)

    def test_inherits_editor(self):
        assert issubclass(ModelGenerationAPI, EditorHandlersMixin)


class TestCoreHandlers:
    def test_health_check_returns_200(self):
        api = ModelGenerationAPI()
        req = APIRequest(method=HTTPMethod.GET, path="/api/v1/health")
        resp = api.health_check(req)
        assert resp.status_code == 200
        assert resp.body["status"] == "healthy"
        assert resp.body["service"] == "model_generation"

    def test_get_api_info_returns_endpoints(self):
        api = ModelGenerationAPI()
        req = APIRequest(method=HTTPMethod.GET, path="/api/v1/info")
        resp = api.get_api_info(req)
        assert resp.status_code == 200
        assert "endpoints" in resp.body
        assert len(resp.body["endpoints"]) > 0

    def test_get_api_info_endpoint_shape(self):
        api = ModelGenerationAPI()
        req = APIRequest(method=HTTPMethod.GET, path="/api/v1/info")
        resp = api.get_api_info(req)
        ep = resp.body["endpoints"][0]
        assert "method" in ep
        assert "path" in ep
        assert "description" in ep
        assert "tags" in ep


class TestInertiaHandlers:
    def test_calculate_inertia_box(self):
        api = ModelGenerationAPI()
        req = APIRequest(
            method=HTTPMethod.POST,
            path="/api/v1/inertia/calculate",
            body={"shape": "box", "mass": 1.0, "dimensions": [0.1, 0.2, 0.3]},
        )
        resp = api.calculate_inertia(req)
        assert resp.status_code == 200
        assert "inertia" in resp.body
        assert "ixx" in resp.body["inertia"]

    def test_calculate_inertia_sphere(self):
        api = ModelGenerationAPI()
        req = APIRequest(
            method=HTTPMethod.POST,
            path="/api/v1/inertia/calculate",
            body={"shape": "sphere", "mass": 1.0, "dimensions": [0.5]},
        )
        resp = api.calculate_inertia(req)
        assert resp.status_code == 200

    def test_calculate_inertia_missing_shape(self):
        api = ModelGenerationAPI()
        req = APIRequest(
            method=HTTPMethod.POST,
            path="/api/v1/inertia/calculate",
            body={"mass": 1.0},
        )
        resp = api.calculate_inertia(req)
        assert resp.status_code == 400

    def test_calculate_inertia_unknown_shape(self):
        api = ModelGenerationAPI()
        req = APIRequest(
            method=HTTPMethod.POST,
            path="/api/v1/inertia/calculate",
            body={"shape": "torus", "mass": 1.0, "dimensions": [1.0]},
        )
        resp = api.calculate_inertia(req)
        assert resp.status_code == 400

    def test_inertia_from_mesh_missing_file(self):
        api = ModelGenerationAPI()
        req = APIRequest(
            method=HTTPMethod.POST,
            path="/api/v1/inertia/from-mesh",
            body={"mass": 1.0},
        )
        resp = api.inertia_from_mesh(req)
        assert resp.status_code == 400

    def test_inertia_from_mesh_missing_mass_and_density(self):
        api = ModelGenerationAPI()
        req = APIRequest(
            method=HTTPMethod.POST,
            path="/api/v1/inertia/from-mesh",
            body={},
            files={"mesh": b"fake_mesh_data"},
        )
        resp = api.inertia_from_mesh(req)
        assert resp.status_code == 400

    def test_inertia_from_mesh_no_trimesh(self):
        """Without trimesh installed, should return 501."""
        import sys
        from unittest.mock import patch

        api = ModelGenerationAPI()
        req = APIRequest(
            method=HTTPMethod.POST,
            path="/api/v1/inertia/from-mesh",
            body={"mass": 1.0},
            files={"mesh": b"fake_mesh_data"},
        )

        with patch.dict(sys.modules, {"trimesh": None}):
            resp = api.inertia_from_mesh(req)
        assert resp.status_code == 501


class TestHandleRequestRouting:
    def test_health_route_via_handle_request(self):
        api = ModelGenerationAPI()
        req = APIRequest(method=HTTPMethod.GET, path="/api/v1/health")
        resp = api.handle_request(req)
        assert resp.status_code == 200

    def test_unknown_route_returns_404(self):
        api = ModelGenerationAPI()
        req = APIRequest(method=HTTPMethod.GET, path="/api/v1/nonexistent")
        resp = api.handle_request(req)
        assert resp.status_code == 404

    def test_precondition_blocks_null_request(self):
        api = ModelGenerationAPI()
        import pytest

        with pytest.raises(ValueError):
            api.handle_request(None)  # type: ignore[arg-type]
