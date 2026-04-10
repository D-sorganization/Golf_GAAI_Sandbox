"""Inertia calculation endpoint handlers for ModelGenerationAPI."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from model_generation.api.models import APIRequest, APIResponse


class InertiaHandlersMixin:
    """Mixin providing inertia calculation endpoints."""

    def _serialize_inertia(self, inertia: Any) -> dict[str, float]:
        """Serialize an inertia object into the API payload shape."""
        return {
            "ixx": inertia.ixx,
            "iyy": inertia.iyy,
            "izz": inertia.izz,
            "ixy": inertia.ixy,
            "ixz": inertia.ixz,
            "iyz": inertia.iyz,
        }

    def _primitive_inertia(
        self,
        shape: str,
        mass: float,
        dimensions: list[float],
        inertia_cls: Any,
    ) -> Any:
        """Calculate inertia for a supported primitive shape."""
        if shape == "box":
            if len(dimensions) != 3:
                raise ValueError("Box requires 3 dimensions")
            return inertia_cls.from_box(mass, *dimensions)
        if shape == "cylinder":
            if len(dimensions) != 2:
                raise ValueError("Cylinder requires 2 dimensions (radius, length)")
            return inertia_cls.from_cylinder(mass, dimensions[0], dimensions[1])
        if shape == "sphere":
            if len(dimensions) != 1:
                raise ValueError("Sphere requires 1 dimension (radius)")
            return inertia_cls.from_sphere(mass, dimensions[0])
        if shape == "capsule":
            if len(dimensions) != 2:
                raise ValueError("Capsule requires 2 dimensions (radius, length)")
            return inertia_cls.from_capsule(mass, dimensions[0], dimensions[1])
        raise ValueError(f"Unknown shape: {shape}")

    def _mesh_inertia_payload(
        self,
        mesh: Any,
        inertia_tensor: Any,
        mass: float,
    ) -> APIResponse:
        """Build the API response for mesh-based inertia."""
        return APIResponse.ok(
            {
                "mass": mass,
                "volume": mesh.volume,
                "center_of_mass": mesh.center_mass.tolist(),
                "inertia": {
                    "ixx": float(inertia_tensor[0, 0]),
                    "iyy": float(inertia_tensor[1, 1]),
                    "izz": float(inertia_tensor[2, 2]),
                    "ixy": float(inertia_tensor[0, 1]),
                    "ixz": float(inertia_tensor[0, 2]),
                    "iyz": float(inertia_tensor[1, 2]),
                },
            }
        )

    def calculate_inertia(self, request: APIRequest) -> APIResponse:
        """Calculate inertia for primitive shape."""
        if not (request is not None):
            raise ValueError("request must be provided")
        from model_generation.core.types import Inertia

        body = request.body or {}

        shape = body.get("shape")
        mass = body.get("mass", 1.0)
        dimensions = body.get("dimensions", [])

        if not shape:
            return APIResponse.error("Missing 'shape' parameter")

        try:
            inertia = self._primitive_inertia(shape, mass, dimensions, Inertia)
        except ValueError as exc:
            return APIResponse.error(str(exc))
        except (KeyError, TypeError) as exc:
            return APIResponse.error(f"Calculation failed: {exc}")

        return APIResponse.ok(
            {
                "shape": shape,
                "mass": mass,
                "dimensions": dimensions,
                "inertia": self._serialize_inertia(inertia),
                "is_positive_definite": inertia.is_positive_definite(),
                "satisfies_triangle_inequality": inertia.satisfies_triangle_inequality(),
            }
        )

    def inertia_from_mesh(self, request: APIRequest) -> APIResponse:
        """Calculate inertia from mesh file."""
        if not (request is not None):
            raise ValueError("request must be provided")
        body = request.body or {}

        mesh_content = request.files.get("mesh")
        if not mesh_content:
            return APIResponse.error("Missing mesh file")

        mass = body.get("mass")
        density = body.get("density")

        if not mass and not density:
            return APIResponse.error("Must provide either 'mass' or 'density'")

        try:
            import trimesh

            with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
                f.write(mesh_content)
                temp_path = f.name

            mesh: Any = trimesh.load(temp_path)

            if density:
                mesh.density = density
                inertia_tensor = mesh.moment_inertia
                calculated_mass = mesh.mass
            else:
                inertia_tensor = mesh.moment_inertia * (mass / mesh.mass)
                calculated_mass = mass

            Path(temp_path).unlink()
            return self._mesh_inertia_payload(mesh, inertia_tensor, calculated_mass)

        except ImportError:
            return APIResponse.error(
                "trimesh library not available for mesh-based inertia calculation",
                501,
            )
        except (PermissionError, OSError) as e:
            return APIResponse.error(f"Mesh processing failed: {e}")
