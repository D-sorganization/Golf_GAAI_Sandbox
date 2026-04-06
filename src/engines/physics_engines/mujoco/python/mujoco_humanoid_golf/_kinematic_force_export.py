from __future__ import annotations

import csv

from ._kinematic_force_context import KinematicForceData


def _build_export_header(nv: int) -> list[str]:
    header = [
        "time",
        "coriolis_power",
        "centrifugal_power",
        "rotational_ke",
        "translational_ke",
    ]
    for index in range(nv):
        header.extend(
            [
                f"coriolis_force_{index}",
                f"gravity_force_{index}",
                f"centrifugal_force_{index}",
            ]
        )
    header.extend(
        [
            "club_coriolis_x",
            "club_coriolis_y",
            "club_coriolis_z",
            "club_centrifugal_x",
            "club_centrifugal_y",
            "club_centrifugal_z",
        ]
    )
    return header


def _build_force_data_row(force_data: KinematicForceData, nv: int) -> list[float]:
    row = [
        force_data.time,
        force_data.coriolis_power,
        force_data.centrifugal_power,
        force_data.rotational_kinetic_energy,
        force_data.translational_kinetic_energy,
    ]
    for index in range(nv):
        row.extend(
            [
                force_data.coriolis_forces[index],
                force_data.gravity_forces[index],
                (
                    force_data.centrifugal_forces[index]
                    if force_data.centrifugal_forces is not None
                    else 0.0
                ),
            ]
        )
    row.extend(
        force_data.club_head_coriolis_force.tolist()
        if force_data.club_head_coriolis_force is not None
        else [0.0, 0.0, 0.0]
    )
    row.extend(
        force_data.club_head_centrifugal_force.tolist()
        if force_data.club_head_centrifugal_force is not None
        else [0.0, 0.0, 0.0]
    )
    return row


def export_kinematic_forces_to_csv(
    force_data_list: list[KinematicForceData],
    filepath: str,
) -> None:
    """Export kinematic force analysis to CSV file."""
    nv = len(force_data_list[0].coriolis_forces)
    with open(filepath, "w", newline="") as file_obj:
        writer = csv.writer(file_obj)
        writer.writerow(_build_export_header(nv))
        for force_data in force_data_list:
            writer.writerow(_build_force_data_row(force_data, nv))
