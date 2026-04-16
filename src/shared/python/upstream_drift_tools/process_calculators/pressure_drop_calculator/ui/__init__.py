"""Pressure drop UI components module.

This module provides human-readable output helpers for the
pressure drop calculator, including table printing, help text,
reference listings, and result formatting.
"""

from .display_helpers import (
    compare_friction_methods,
    generate_recommendations,
    list_fittings,
    list_flow_units,
    list_gas_components,
    list_materials,
    list_pipe_sizes,
    print_results,
    show_help,
    wrap_text,
)

__all__ = [
    "compare_friction_methods",
    "generate_recommendations",
    "list_fittings",
    "list_flow_units",
    "list_gas_components",
    "list_materials",
    "list_pipe_sizes",
    "print_results",
    "show_help",
    "wrap_text",
]
