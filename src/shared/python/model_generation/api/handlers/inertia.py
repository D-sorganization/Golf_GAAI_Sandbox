"""Inertia calculation endpoint handlers for ModelGenerationAPI."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from model_generation.api.models import APIRequest, APIResponse


class InertiaHandlersMixin:
    """Mixin providing inertia calculation endpoints."""

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
            if shape == "box":
                if len(dimensions) != 3:
                    return APIResponse.error("Box requires 3 dimensions")
                inertia = Inertia.from_box(mass, *dimensions)

            elif shape == "cylinder":
                if len(dimensions) != 2:
                    return APIResponse.error(
                        "Cylinder requires 2 dimensions (radius, length)"
                    )
                inertia = Inertia.from_cylinder(mass, dimensions[0], dimensions[1])

            elif shape == "sphere":
                if len(dimensions) != 1:
                    return APIResponse.error("Sphere requires 1 dimension (radius)")
                inertia = Inertia.from_sphere(mass, dimensions[0])

            elif shape == "capsule":
                if len(dimensions) != 2:
                    return APIResponse.error(
                        "Capsule requires 2 dimensions (radius, length)"
                    )
                inertia = Inertia.from_capsule(mass, dimensions[0], dimensions[1])

            else:
                return APIResponse.error(f"Unknown shape: {shape}")

        except (KeyError, ValueError, TypeError) as e:
            return APIResponse.error(f"Calculation failed: {e}")

        return APIResponse.ok(
            {
                "shape": shape,
                "mass": mass,
                "dimensions": dimensions,
                "inertia": {
                    "ixx": inertia.ixx,
                    "iyy": inertia.iyy,
                    "izz": inertia.izz,
                    "ixy": inertia.ixy,
                    "ixz": inertia.ixz,
                    "iyz": inertia.iyz,
                },
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
                volume = mesh.volume
                inertia_tensor = mesh.moment_inertia * (mass / mesh.mass)
                calculated_mass = mass

            Path(temp_path).unlink()

            return APIResponse.ok(
                {
                    "mass": calculated_mass,
                    "volume": volume if density else mesh.volume,
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

        except ImportError:
            return APIResponse.error(
                "trimesh library not available for mesh-based inertia calculation",
                501,
            )
        except (PermissionError, OSError) as e:
            return APIResponse.error(f"Mesh processing failed: {e}")
