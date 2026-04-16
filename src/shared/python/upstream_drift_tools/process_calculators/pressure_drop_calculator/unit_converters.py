"""Unit conversion helpers for the pressure drop calculator.

Provides temperature and pressure unit conversions used by the
high-level calculation API.
"""

from __future__ import annotations

_PRESSURE_TO_PA: dict[str, float] = {
    "Pa": 1.0,
    "kPa": 1000.0,
    "MPa": 1e6,
    "bar": 1e5,
    "mbar": 100.0,
    "atm": 101325.0,
    "psi": 6894.76,
    "psia": 6894.76,
    "psig": 6894.76,  # Note: gauge pressure, user should handle offset
}


def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """Convert temperature between K, C, and F.

    Args:
        value: Temperature value
        from_unit: Source unit ('K', 'C', or 'F')
        to_unit: Target unit ('K', 'C', or 'F')

    Returns:
        Converted temperature value

    Raises:
        ValueError: If either unit is not recognised

    Example:
        >>> convert_temperature(0, 'C', 'K')
        273.15
        >>> convert_temperature(212, 'F', 'C')
        100.0
    """
    from_upper = from_unit.upper()
    to_upper = to_unit.upper()

    if from_upper == "K":
        temp_k = value
    elif from_upper == "C":
        temp_k = value + 273.15
    elif from_upper == "F":
        temp_k = (value - 32) * 5 / 9 + 273.15
    else:
        raise ValueError(f"Unknown temperature unit: {from_unit}")

    if to_upper == "K":
        return temp_k
    if to_upper == "C":
        return temp_k - 273.15
    if to_upper == "F":
        return (temp_k - 273.15) * 9 / 5 + 32
    raise ValueError(f"Unknown temperature unit: {to_unit}")


def convert_pressure(value: float, from_unit: str, to_unit: str) -> float:
    """Convert pressure between Pa, kPa, MPa, bar, mbar, atm, psi, psia, psig.

    Args:
        value: Pressure value
        from_unit: Source unit
        to_unit: Target unit

    Returns:
        Converted pressure value

    Raises:
        ValueError: If either unit is not recognised

    Example:
        >>> convert_pressure(1, 'bar', 'Pa')
        100000.0
        >>> convert_pressure(101325, 'Pa', 'atm')
        1.0
    """
    if from_unit not in _PRESSURE_TO_PA:
        raise ValueError(f"Unknown pressure unit: {from_unit}")
    if to_unit not in _PRESSURE_TO_PA:
        raise ValueError(f"Unknown pressure unit: {to_unit}")

    pa = value * _PRESSURE_TO_PA[from_unit]
    return pa / _PRESSURE_TO_PA[to_unit]


__all__ = [
    "convert_pressure",
    "convert_temperature",
]
