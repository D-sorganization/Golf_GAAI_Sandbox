"""Conversion endpoint handlers for ModelGenerationAPI."""

from __future__ import annotations

from typing import Any

from model_generation.api.models import APIRequest, APIResponse


class ConversionHandlersMixin:
    """Mixin providing format conversion endpoints."""

    def _extract_simscape_content(
        self,
        request: APIRequest,
        body: dict[str, object],
    ) -> tuple[str | None, str]:
        """Extract uploaded or inline Simscape content and format."""
        if "file" in request.files:
            content = request.files["file"].decode("utf-8", errors="ignore")
            format_type = "xml" if content.strip().startswith(("<?xml", "<")) else "mdl"
            return content, format_type
        if "content" in body:
            return str(body["content"]), str(body.get("format", "mdl"))
        return None, "mdl"

    def _build_simscape_response(self, request: APIRequest, result: Any) -> APIResponse:
        """Build the successful Simscape conversion response."""
        response_data = {
            "success": True,
            "robot_name": result.robot_name,
            "links": len(result.links),
            "joints": len(result.joints),
            "warnings": result.warnings,
            "urdf": result.urdf_string,
        }
        if (
            request.query_params.get("download") == "true"
            and result.urdf_string is not None
        ):
            return APIResponse.file(result.urdf_string, f"{result.robot_name}.urdf")
        return APIResponse.ok(response_data)

    def convert_simscape_to_urdf(self, request: APIRequest) -> APIResponse:
        """Convert SimScape MDL/SLX to URDF."""
        if not (request is not None):
            raise ValueError("request must be provided")
        from model_generation.converters.simscape import (
            ConversionConfig,
            SimscapeToURDFConverter,
        )

        body = request.body or {}

        content, format_type = self._extract_simscape_content(request, body)
        if not content:
            return APIResponse.error("Missing model content or file")

        robot_name = str(body.get("robot_name", "converted_robot"))
        config = ConversionConfig(robot_name=robot_name)
        result = SimscapeToURDFConverter(config).convert_string(content, format_type)

        if not result.success:
            return APIResponse.error(
                "; ".join(result.errors),
                status_code=422,
            )
        return self._build_simscape_response(request, result)

    def convert_mjcf_to_urdf(self, request: APIRequest) -> APIResponse:
        """Convert MJCF to URDF."""
        if not (request is not None):
            raise ValueError("request must be provided")
        from model_generation.converters.mjcf_converter import MJCFConverter

        body = request.body or {}

        content = body.get("content") or (
            request.files.get("file", b"").decode("utf-8") if request.files else None
        )

        if not content:
            return APIResponse.error("Missing MJCF content")

        converter = MJCFConverter()

        try:
            urdf_string = converter.mjcf_to_urdf(content)
        except (ValueError, KeyError, OSError) as e:
            return APIResponse.error(f"Conversion failed: {e}", 422)

        robot_name = body.get("robot_name", "converted")

        if request.query_params.get("download") == "true":
            return APIResponse.file(urdf_string, f"{robot_name}.urdf")

        return APIResponse.ok({"urdf": urdf_string})

    def convert_urdf_to_mjcf(self, request: APIRequest) -> APIResponse:
        """Convert URDF to MJCF."""
        if not (request is not None):
            raise ValueError("request must be provided")
        from model_generation.converters.mjcf_converter import MJCFConverter

        body = request.body or {}

        content = body.get("content") or (
            request.files.get("file", b"").decode("utf-8") if request.files else None
        )

        if not content:
            return APIResponse.error("Missing URDF content")

        converter = MJCFConverter()

        try:
            mjcf_string = converter.urdf_to_mjcf(content)
        except (ValueError, KeyError, OSError) as e:
            return APIResponse.error(f"Conversion failed: {e}", 422)

        robot_name = body.get("robot_name", "converted")

        if request.query_params.get("download") == "true":
            return APIResponse.file(mjcf_string, f"{robot_name}.xml", "application/xml")

        return APIResponse.ok({"mjcf": mjcf_string})
