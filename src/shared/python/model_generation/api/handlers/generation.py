"""Generation endpoint handlers for ModelGenerationAPI."""

from __future__ import annotations

from model_generation.api.models import APIRequest, APIResponse


class GenerationHandlersMixin:
    """Mixin providing URDF generation endpoints."""

    def generate_humanoid(self, request: APIRequest) -> APIResponse:
        """Generate humanoid URDF."""
        if not (request is not None):
            raise ValueError("request must be provided")
        from model_generation.builders.parametric_builder import ParametricBuilder

        body = request.body or {}
        robot_name = body.get("name", "humanoid")
        height = body.get("height", 1.7)
        mass = body.get("mass", 70.0)

        builder = ParametricBuilder(robot_name=robot_name)

        proportions = body.get("proportions", {})
        builder.set_parameters(height_m=height, mass_kg=mass, **proportions)

        builder.add_humanoid_segments()
        result = builder.build()

        if not result.success:
            return APIResponse.error(result.error_message or "Build failed")

        urdf_string = result.urdf_xml

        if request.query_params.get("download") == "true" and urdf_string is not None:
            return APIResponse.file(urdf_string, f"{robot_name}.urdf")

        return APIResponse.ok(
            {
                "robot_name": robot_name,
                "links": len(result.links),
                "joints": len(result.joints),
                "urdf": urdf_string,
            }
        )

    def generate_from_params(self, request: APIRequest) -> APIResponse:
        """Generate URDF from detailed parameters."""
        if not (request is not None):
            raise ValueError("request must be provided")
        from model_generation.builders.manual_builder import ManualBuilder
        from model_generation.core.types import Joint, Link

        body = request.body or {}

        if "links" not in body:
            return APIResponse.error("Missing 'links' in request body")

        robot_name = body.get("name", "robot")
        builder = ManualBuilder(robot_name=robot_name)

        for link_data in body.get("links", []):
            link = Link.from_dict(link_data)
            builder.add_link(link)

        for joint_data in body.get("joints", []):
            joint = Joint.from_dict(joint_data)
            builder.add_joint(joint)

        result = builder.build()

        if not result.success:
            return APIResponse.error(result.error_message or "Build failed")

        urdf_string = result.urdf_xml

        if request.query_params.get("download") == "true" and urdf_string is not None:
            return APIResponse.file(urdf_string, f"{robot_name}.urdf")

        return APIResponse.ok(
            {
                "robot_name": robot_name,
                "links": len(result.links),
                "joints": len(result.joints),
                "urdf": urdf_string,
            }
        )
