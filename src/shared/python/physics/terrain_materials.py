"""Terrain types and surface materials for golf simulation.

Defines :class:`TerrainType` (fairway, rough, green, bunker, etc.) together
with the :class:`SurfaceMaterial` dataclass describing physical properties
for each surface (friction, restitution, hardness, compressibility, ...).

A ``MATERIALS`` registry provides tuned defaults for common surfaces and
``TERRAIN_MATERIAL_MAP`` maps each :class:`TerrainType` to its canonical
material name. This module is pure data / validation — no runtime
dependencies beyond :mod:`dataclasses` and :mod:`enum`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TerrainType(Enum):
    """Golf course terrain types."""

    FAIRWAY = auto()
    ROUGH = auto()
    GREEN = auto()
    BUNKER = auto()
    TEE = auto()
    FRINGE = auto()
    WATER = auto()
    CART_PATH = auto()
    OUT_OF_BOUNDS = auto()


@dataclass
class SurfaceMaterial:
    """Physical properties of a surface material.

    Attributes:
        name: Identifier for this material
        friction_coefficient: Coulomb friction coefficient (mu)
        rolling_resistance: Rolling resistance coefficient
        restitution: Coefficient of restitution (bounce)
        hardness: Surface hardness (0=soft, 1=hard)
        grass_height_m: Height of grass in meters
        compressibility: Surface compressibility (0=rigid, 1=very soft)
        compression_damping: Damping ratio for compression (0-1)
        turf_density: Turf/grass density affecting resistance (kg/m^3)
        moisture_content: Moisture level affecting properties (0=dry, 1=saturated)
    """

    name: str
    friction_coefficient: float = 0.5
    rolling_resistance: float = 0.1
    restitution: float = 0.6
    hardness: float = 0.7
    grass_height_m: float = 0.0
    compressibility: float = 0.0
    compression_damping: float = 0.3
    turf_density: float = 0.0
    moisture_content: float = 0.3

    def __post_init__(self) -> None:
        """Validate material properties."""
        if self.friction_coefficient < 0:
            raise ValueError("friction_coefficient must be non-negative")
        if self.rolling_resistance < 0:
            raise ValueError("rolling_resistance must be non-negative")
        if not 0 <= self.restitution <= 1:
            raise ValueError("restitution must be between 0 and 1")
        if not 0 <= self.hardness <= 1:
            raise ValueError("hardness must be between 0 and 1")
        if self.grass_height_m < 0:
            raise ValueError("grass_height_m must be non-negative")
        if not 0 <= self.compressibility <= 1:
            raise ValueError("compressibility must be between 0 and 1")
        if not 0 <= self.compression_damping <= 1:
            raise ValueError("compression_damping must be between 0 and 1")
        if not 0 <= self.moisture_content <= 1:
            raise ValueError("moisture_content must be between 0 and 1")

    @property
    def is_compressible(self) -> bool:
        """Check if this material is compressible."""
        return self.compressibility > 0.01

    def get_effective_stiffness(self, base_stiffness: float = 1e5) -> float:
        """Get effective stiffness considering compressibility.

        Args:
            base_stiffness: Base stiffness for rigid surfaces (N/m)

        Returns:
            Effective stiffness (N/m)
        """
        # Higher compressibility = lower stiffness
        return base_stiffness * (1.0 - 0.9 * self.compressibility)

    def get_max_compression_depth(self) -> float:
        """Get maximum compression depth in meters.

        Returns:
            Maximum compression depth based on grass height and compressibility
        """
        # Turf can compress up to 80% of grass height
        base_depth = self.grass_height_m * 0.8 * self.compressibility
        # Moisture increases compression
        moisture_factor = 1.0 + 0.5 * self.moisture_content
        return base_depth * moisture_factor


# Predefined materials for common terrain types
MATERIALS: dict[str, SurfaceMaterial] = {
    "fairway": SurfaceMaterial(
        name="fairway",
        friction_coefficient=0.45,
        rolling_resistance=0.08,
        restitution=0.65,
        hardness=0.75,
        grass_height_m=0.015,
        compressibility=0.15,  # Slight compression
        compression_damping=0.25,
        turf_density=120.0,  # kg/m^3
        moisture_content=0.3,
    ),
    "rough": SurfaceMaterial(
        name="rough",
        friction_coefficient=0.55,
        rolling_resistance=0.20,
        restitution=0.45,
        hardness=0.65,
        grass_height_m=0.050,
        compressibility=0.35,  # More compressible
        compression_damping=0.40,
        turf_density=80.0,
        moisture_content=0.35,
    ),
    "green": SurfaceMaterial(
        name="green",
        friction_coefficient=0.35,
        rolling_resistance=0.05,
        restitution=0.70,
        hardness=0.80,
        grass_height_m=0.004,
        compressibility=0.05,  # Very firm
        compression_damping=0.15,
        turf_density=200.0,
        moisture_content=0.25,
    ),
    "bunker": SurfaceMaterial(
        name="bunker",
        friction_coefficient=0.80,
        rolling_resistance=0.40,
        restitution=0.30,
        hardness=0.30,
        grass_height_m=0.0,
        compressibility=0.70,  # Sand is highly compressible
        compression_damping=0.60,
        turf_density=1500.0,  # Sand density
        moisture_content=0.10,
    ),
    "tee": SurfaceMaterial(
        name="tee",
        friction_coefficient=0.45,
        rolling_resistance=0.08,
        restitution=0.65,
        hardness=0.80,
        grass_height_m=0.010,
        compressibility=0.10,  # Firm, well-maintained
        compression_damping=0.20,
        turf_density=150.0,
        moisture_content=0.25,
    ),
    "fringe": SurfaceMaterial(
        name="fringe",
        friction_coefficient=0.42,
        rolling_resistance=0.10,
        restitution=0.60,
        hardness=0.75,
        grass_height_m=0.012,
        compressibility=0.12,
        compression_damping=0.22,
        turf_density=140.0,
        moisture_content=0.28,
    ),
    "cart_path": SurfaceMaterial(
        name="cart_path",
        friction_coefficient=0.70,
        rolling_resistance=0.02,
        restitution=0.80,
        hardness=0.95,
        grass_height_m=0.0,
        compressibility=0.0,  # Rigid surface
        compression_damping=0.0,
        turf_density=0.0,
        moisture_content=0.0,
    ),
    "water": SurfaceMaterial(
        name="water",
        friction_coefficient=0.01,
        rolling_resistance=0.90,
        restitution=0.10,
        hardness=0.0,
        grass_height_m=0.0,
        compressibility=1.0,  # Water compresses (ball sinks)
        compression_damping=0.90,
        turf_density=1000.0,  # Water density
        moisture_content=1.0,
    ),
    # New compressible turf materials
    "soft_turf": SurfaceMaterial(
        name="soft_turf",
        friction_coefficient=0.50,
        rolling_resistance=0.15,
        restitution=0.50,
        hardness=0.50,
        grass_height_m=0.025,
        compressibility=0.45,  # Notably compressible
        compression_damping=0.45,
        turf_density=100.0,
        moisture_content=0.45,
    ),
    "wet_fairway": SurfaceMaterial(
        name="wet_fairway",
        friction_coefficient=0.35,
        rolling_resistance=0.12,
        restitution=0.55,
        hardness=0.60,
        grass_height_m=0.015,
        compressibility=0.30,  # Wet ground compresses more
        compression_damping=0.35,
        turf_density=120.0,
        moisture_content=0.70,
    ),
    "divot": SurfaceMaterial(
        name="divot",
        friction_coefficient=0.60,
        rolling_resistance=0.25,
        restitution=0.40,
        hardness=0.40,
        grass_height_m=0.005,  # Damaged turf
        compressibility=0.50,  # Loose soil
        compression_damping=0.50,
        turf_density=90.0,
        moisture_content=0.35,
    ),
}

# Mapping from terrain type to default material
TERRAIN_MATERIAL_MAP: dict[TerrainType, str] = {
    TerrainType.FAIRWAY: "fairway",
    TerrainType.ROUGH: "rough",
    TerrainType.GREEN: "green",
    TerrainType.BUNKER: "bunker",
    TerrainType.TEE: "tee",
    TerrainType.FRINGE: "fringe",
    TerrainType.CART_PATH: "cart_path",
    TerrainType.WATER: "water",
    TerrainType.OUT_OF_BOUNDS: "rough",
}


__all__ = [
    "MATERIALS",
    "TERRAIN_MATERIAL_MAP",
    "SurfaceMaterial",
    "TerrainType",
]
