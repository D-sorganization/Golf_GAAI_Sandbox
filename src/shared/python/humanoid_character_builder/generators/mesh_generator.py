"""Shared mesh-generation contracts and backend factory."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from humanoid_character_builder.core.body_parameters import BodyParameters

logger = logging.getLogger(__name__)

# Optional dependency availability flags are intentionally kept here so tests
# and downstream callers can continue to monkeypatch the historic import path.
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

    PRIMITIVE = "primitive"
    MAKEHUMAN = "makehuman"
    SMPLX = "smplx"
    CUSTOM = "custom"


@dataclass
class GeneratedMeshResult:
    """Result of mesh generation."""

    success: bool
    mesh_paths: dict[str, Path] = field(default_factory=dict)
    collision_paths: dict[str, Path] = field(default_factory=dict)
    texture_paths: dict[str, Path] = field(default_factory=dict)
    vertex_groups: dict[str, list[int]] = field(default_factory=dict)
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class MeshGeneratorInterface(ABC):
    """Abstract interface for mesh generation backends."""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return the backend name."""
        ...

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Return whether the backend is installed and configured."""
        ...

    @abstractmethod
    def generate(
        self,
        params: BodyParameters,
        output_dir: Path,
        **kwargs: Any,
    ) -> GeneratedMeshResult:
        """Generate meshes for the given body parameters."""
        ...

    @abstractmethod
    def get_supported_segments(self) -> list[str]:
        """Return segment names this backend can generate."""
        ...


from humanoid_character_builder.generators.makehuman_mesh_generator import (  # noqa: E402
    MakeHumanMeshGenerator,
)
from humanoid_character_builder.generators.primitive_mesh_generator import (  # noqa: E402
    PrimitiveMeshGenerator,
)
from humanoid_character_builder.generators.smplx_mesh_generator import (  # noqa: E402
    SMPLXMeshGenerator,
)


class MeshGenerator:
    """Factory class for creating mesh generators."""

    _generators: dict[MeshGeneratorBackend, type[MeshGeneratorInterface]] = {
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
        """Create a mesh generator for the specified backend."""
        normalized_backend = _normalize_backend(backend)
        generator_class = cls._generators.get(normalized_backend)
        if generator_class is None:
            raise ValueError(f"Unknown backend: {normalized_backend}")
        return generator_class(**kwargs)

    @classmethod
    def get_available_backends(cls) -> list[MeshGeneratorBackend]:
        """Return backends whose dependencies and configuration are present."""
        available: list[MeshGeneratorBackend] = []
        for backend, generator_class in cls._generators.items():
            if _backend_is_available(backend, generator_class):
                available.append(backend)
        return available

    @classmethod
    def get_best_available(cls) -> MeshGeneratorInterface:
        """Return the preferred available backend."""
        for backend in _backend_preference():
            try:
                generator = cls.create(backend)
            except (ImportError, RuntimeError, OSError) as exc:
                logger.debug("Backend %s not available: %s", backend.value, exc)
                continue
            if generator.is_available:
                return generator
        return PrimitiveMeshGenerator()


def _normalize_backend(backend: MeshGeneratorBackend | str) -> MeshGeneratorBackend:
    if isinstance(backend, str):
        return MeshGeneratorBackend(backend.lower())
    return backend


def _backend_is_available(
    backend: MeshGeneratorBackend,
    generator_class: type[MeshGeneratorInterface],
) -> bool:
    try:
        return generator_class().is_available
    except (ImportError, RuntimeError, OSError) as exc:
        logger.debug("Backend %s not available: %s", backend.value, exc)
        return False


def _backend_preference() -> tuple[MeshGeneratorBackend, ...]:
    return (
        MeshGeneratorBackend.MAKEHUMAN,
        MeshGeneratorBackend.SMPLX,
        MeshGeneratorBackend.PRIMITIVE,
    )


__all__ = [
    "GeneratedMeshResult",
    "MakeHumanMeshGenerator",
    "MeshGenerator",
    "MeshGeneratorBackend",
    "MeshGeneratorInterface",
    "PrimitiveMeshGenerator",
    "SMPLXMeshGenerator",
    "SMPLX_AVAILABLE",
    "TRIMESH_AVAILABLE",
]
