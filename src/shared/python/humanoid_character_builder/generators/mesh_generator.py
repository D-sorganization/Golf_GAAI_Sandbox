"""
Mesh generation interfaces for humanoid character builder.

This module defines interfaces for mesh generation backends
(MakeHuman, SMPL, etc.) and provides a factory for creating
mesh generators.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from humanoid_character_builder.core.body_parameters import BodyParameters

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency availability flags (mock-patchable in tests)
# ---------------------------------------------------------------------------

try:
    import smplx as _smplx_module  # type: ignore[import-untyped]

    SMPLX_AVAILABLE = True
except ImportError:
    _smplx_module = None  # type: ignore[assignment]
    SMPLX_AVAILABLE = False

try:
    import trimesh as _trimesh_module  # type: ignore[import-untyped]

    TRIMESH_AVAILABLE = True
except ImportError:
    _trimesh_module = None  # type: ignore[assignment]
    TRIMESH_AVAILABLE = False


class MeshGeneratorBackend(Enum):
    """Available mesh generation backends."""

    PRIMITIVE = "primitive"  # Generate primitive shapes (built-in)
    MAKEHUMAN = "makehuman"  # MakeHuman integration
    SMPLX = "smplx"  # SMPL-X body model
    CUSTOM = "custom"  # Custom mesh provider


@dataclass
class GeneratedMeshResult:
    """Result of mesh generation."""

    # Whether generation was successful
    success: bool

    # Path to generated mesh files (segment name -> path)
    mesh_paths: dict[str, Path] = field(default_factory=dict)

    # Path to collision mesh files
    collision_paths: dict[str, Path] = field(default_factory=dict)

    # Path to texture files
    texture_paths: dict[str, Path] = field(default_factory=dict)

    # Vertex group mapping (for segmentation)
    vertex_groups: dict[str, list[int]] = field(default_factory=dict)

    # Error message if failed
    error_message: str | None = None

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)


class MeshGeneratorInterface(ABC):
    """
    Abstract interface for mesh generation backends.

    Implement this interface to add new mesh generation sources
    (MakeHuman, SMPL, etc.).
    """

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return the backend name."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is available (installed, configured)."""
        ...

    @abstractmethod
    def generate(
        self,
        params: BodyParameters,
        output_dir: Path,
        **kwargs: Any,
    ) -> GeneratedMeshResult:
        """
        Generate meshes for the given body parameters.

        Args:
            params: Body parameters
            output_dir: Directory to write mesh files
            **kwargs: Backend-specific options

        Returns:
            GeneratedMeshResult with paths to generated files
        """
        ...

    @abstractmethod
    def get_supported_segments(self) -> list[str]:
        """Return list of segment names this backend can generate."""
        ...


class MeshGenerator:
    """
    Factory class for creating mesh generators.

    Provides a unified interface to multiple mesh generation backends.
    """

    @classmethod
    def _get_generators(
        cls,
    ) -> dict[MeshGeneratorBackend, type[MeshGeneratorInterface]]:
        from .makehuman_mesh_generator import MakeHumanMeshGenerator
        from .primitive_mesh_generator import PrimitiveMeshGenerator
        from .smplx_mesh_generator import SMPLXMeshGenerator

        return {
            MeshGeneratorBackend.PRIMITIVE: PrimitiveMeshGenerator,
            MeshGeneratorBackend.MAKEHUMAN: MakeHumanMeshGenerator,
            MeshGeneratorBackend.SMPLX: SMPLXMeshGenerator,
        }

    @classmethod
    def create(
        cls,
        backend: MeshGeneratorBackend | str = MeshGeneratorBackend.PRIMITIVE,
        **kwargs: Any,
    ) -> MeshGeneratorInterface:
        """
        Create a mesh generator for the specified backend.

        Args:
            backend: Backend to use
            **kwargs: Backend-specific initialization options

        Returns:
            MeshGeneratorInterface instance
        """
        if isinstance(backend, str):
            backend = MeshGeneratorBackend(backend.lower())

        generators = cls._get_generators()
        generator_class = generators.get(backend)
        if generator_class is None:
            raise ValueError(f"Unknown backend: {backend}")

        return generator_class(**kwargs)

    @classmethod
    def get_available_backends(cls) -> list[MeshGeneratorBackend]:
        """Return list of available backends."""
        available = []
        generators = cls._get_generators()
        for backend, generator_class in generators.items():
            try:
                generator = generator_class()
                if generator.is_available:
                    available.append(backend)
            except (ImportError, RuntimeError, OSError) as e:
                logger.debug("Backend %s not available: %s", backend.value, e)
        return available

    @classmethod
    def get_best_available(cls) -> MeshGeneratorInterface:
        """
        Get the best available mesh generator.

        Preference order: MakeHuman > SMPL-X > Primitive
        """
        preference = [
            MeshGeneratorBackend.MAKEHUMAN,
            MeshGeneratorBackend.SMPLX,
            MeshGeneratorBackend.PRIMITIVE,
        ]

        for backend in preference:
            try:
                generator = cls.create(backend)
                if generator.is_available:
                    return generator
            except (ImportError, RuntimeError, OSError) as e:
                logger.debug("Backend %s not available: %s", backend.value, e)
                continue

        # Final fallback
        from .primitive_mesh_generator import PrimitiveMeshGenerator

        return PrimitiveMeshGenerator()
