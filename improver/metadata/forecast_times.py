# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of 'IMPROVER' and is released under the BSD 3-Clause license.
# See LICENSE in the root of the repository for full licensing details.
"""Utilities to manipulate forecast time coordinates"""

import warnings
from datetime import datetime
from typing import List, Optional, Union

import iris
import numpy as np
from cf_units import Unit
from iris.coords import AuxCoord, Coord, DimCoord
from iris.cube import Cube, CubeList
from iris.exceptions import CoordinateNotFoundError

from improver.metadata.check_datatypes import check_mandatory_standards
from improver.metadata.constants import FLOAT_TYPES
from improver.metadata.constants.time_types import TIME_COORDS, TimeSpec
from improver.utilities.round import round_close
from improver.utilities.temporal import cycletime_to_datetime


def forecast_period_coord(
    cube: Cube, force_lead_time_calculation: bool = False
) -> Coord:
    """
    Return the lead time coordinate (forecast_period) from a cube, either by
    reading an existing forecast_period coordinate, or by calculating the
    difference between time and forecast_reference_time or blend_time.

    Args:
        cube:
            Cube from which the lead times will be determined.
        force_lead_time_calculation:
            Force the lead time to be calculated from the
            reference time and the time coordinates, even if
            the forecast_period coordinate exists. Default is False.

    Returns:
        New forecast_period coord. A DimCoord is returned if the
        forecast_period coord is already present in the cube as a
        DimCoord and this coord does not need changing, otherwise
        it will be an AuxCoord.
    """
    create_dim_coord = False
    coord_attributes = {}
    frt_coord = cube.coords("forecast_reference_time")
    blend_time_coord = cube.coords("blend_time")
    reference_coord = frt_coord if frt_coord else blend_time_coord
    if frt_coord and blend_time_coord:
        if not frt_coord[0].points == blend_time_coord[0].points:
            raise ValueError(
                "Reference time coords do not match. forecast_reference_time is "
                f"{frt_coord[0].cell(0).point}; blend_time is {blend_time_coord[0].cell(0).point}"
            )

    if cube.coords("forecast_period"):
        coord_attributes = cube.coord("forecast_period").attributes
        if isinstance(cube.coord("forecast_period"), DimCoord):
            create_dim_coord = True

    if cube.coords("forecast_period") and not force_lead_time_calculation:
        result_coord = cube.coord("forecast_period").copy()

    elif cube.coords("time") and reference_coord:
        # Cube must adhere to mandatory standards for safe time calculations
        check_mandatory_standards(cube)
        # Try to calculate forecast period from forecast reference time and
        # time coordinates
        result_coord = _calculate_forecast_period(
            cube.coord("time"),
            cube.coord(reference_coord[0]),
            dim_coord=create_dim_coord,
        )
        result_coord.attributes.update(coord_attributes)

    else:
        msg = (
            "The forecast period coordinate is not available within {}."
            "The time coordinate and (forecast_reference_time or blend_time) "
            "coordinate were also not available for calculating "
            "the forecast_period.".format(cube)
        )
        raise CoordinateNotFoundError(msg)

    return result_coord


def _calculate_forecast_period(
    time_coord: Coord,
    frt_coord: Coord,
    dim_coord: bool = False,
    coord_spec: TimeSpec = TIME_COORDS["forecast_period"],
) -> Coord:
    """
    Calculate a forecast period from existing time and forecast reference
    time coordinates.

    Args:
        time_coord:
            Time coordinate
        frt_coord:
            Forecast reference coordinate
        dim_coord:
            If true, create an iris.coords.DimCoord instance.  Default is to
            create an iris.coords.AuxCoord.
        coord_spec:
            Specification of units and dtype for the forecast_period
            coordinate.

    Returns:
        Forecast period coordinate corresponding to the input times and
        forecast reference times specified

    Warns:
        UserWarning: If any calculated forecast periods are negative
    """
    # use cell() access method to get datetime.datetime instances
    time_points = np.array([c.point for c in time_coord.cells()])
    forecast_reference_time_points = np.array([c.point for c in frt_coord.cells()])
    required_lead_times = time_points - forecast_reference_time_points
    required_lead_times = np.array([x.total_seconds() for x in required_lead_times])

    if time_coord.bounds is not None:
        time_bounds = np.array([c.bound for c in time_coord.cells()])
        required_lead_time_bounds = time_bounds - forecast_reference_time_points
        required_lead_time_bounds = np.array(
            [[b.total_seconds() for b in x] for x in required_lead_time_bounds]
        )
    else:
        required_lead_time_bounds = None

    coord_type = DimCoord if dim_coord else AuxCoord
    result_coord = coord_type(
        required_lead_times,
        standard_name="forecast_period",
        bounds=required_lead_time_bounds,
        units="seconds",
    )

    result_coord.convert_units(coord_spec.units)

    if coord_spec.dtype not in FLOAT_TYPES:
        result_coord.points = round_close(result_coord.points)
        if result_coord.bounds is not None:
            result_coord.bounds = round_close(result_coord.bounds)

    result_coord.points = result_coord.points.astype(coord_spec.dtype)
    if result_coord.bounds is not None:
        result_coord.bounds = result_coord.bounds.astype(coord_spec.dtype)

    if np.any(result_coord.points < 0):
        msg = (
            "The values for the time {} and "
            "forecast_reference_time {} coordinates from the "
            "input cube have produced negative values for the "
            "forecast_period. A forecast does not generate "
            "values in the past."
        ).format(time_coord.points, frt_coord.points)
        warnings.warn(msg)

    return result_coord


def _create_frt_type_coord(
    cube: Cube, point: datetime, name: str = "forecast_reference_time"
) -> DimCoord:
    """Create a new auxiliary coordinate based on forecast reference time

    Args:
        cube:
            Input cube with scalar forecast reference time coordinate
        points
            Single datetime point for output coord
        name
            Name of aux coord to be returned

    Returns:
        New auxiliary coordinate
    """
    frt_coord_name = "forecast_reference_time"
    coord_type_spec = TIME_COORDS[frt_coord_name]
    coord_units = Unit(coord_type_spec.units)
    new_points = round_close([coord_units.date2num(point)], dtype=coord_type_spec.dtype)
    try:
        new_coord = DimCoord(new_points, standard_name=name, units=coord_units)
    except ValueError:
        new_coord = DimCoord(new_points, long_name=name, units=coord_units)
    return new_coord


def add_blend_time(cube: Cube, cycletime: str) -> None:
    """
    Function to add scalar blend time coordinate to a blended cube based
    on current cycle time.  Modifies cube in place.

     Args:
        cubes:
            Cube to add blend time coordinate
        cycletime:
            Required blend time in a YYYYMMDDTHHMMZ format e.g. 20171122T0100Z
    """
    cycle_datetime = cycletime_to_datetime(cycletime)
    blend_coord = _create_frt_type_coord(cube, cycle_datetime, name="blend_time")
    cube.add_aux_coord(blend_coord, data_dims=None)


def rebadge_forecasts_as_latest_cycle(
    cubes: Union[CubeList, List[Cube]], cycletime: Optional[str] = None
) -> CubeList:
    """
    Function to update the forecast_reference_time and forecast_period
    on a list of input forecasts to match either a given cycletime, or
    the most recent forecast in the list (proxy for the current cycle).

    Args:
        cubes:
            Cubes that will have their forecast_reference_time and
            forecast_period updated.
        cycletime:
            Required forecast reference time in a YYYYMMDDTHHMMZ format
            e.g. 20171122T0100Z. If None, the latest forecast reference
            time is used.

    Returns:
        Updated cubes
    """
    if cycletime is None and len(cubes) == 1:
        return cubes
    cycle_datetime = (
        _find_latest_cycletime(cubes)
        if cycletime is None
        else cycletime_to_datetime(cycletime)
    )
    return unify_cycletime(cubes, cycle_datetime)


def unify_cycletime(
    cubes: Union[CubeList, List[Cube]],
    cycletime: datetime,
    target_coords: List[str] = ["forecast_reference_time"],
) -> CubeList:
    """
    Function to unify the target_coords times and update forecast_period. The
    target_coords variable should be a list containing one or both of
    "forecast_reference_time" and "blend_time". The cycletime specified is
    used as the new value for the target_coord, and the forecast_period is
    recalculated using the time coordinate and updated target_coord.

    Args:
        cubes:
            Cubes that will have their forecast_reference_time / blend_time and
            forecast_period updated. Any bounds on the forecast_reference_time /
            blend_time coordinate will be discarded.
        cycletime:
            Datetime for the cycletime that will be used to replace the
            forecast_reference_time / blend_time on the individual cubes.
        target_coords:
            A list of coordinates that relate to cycletime that should be updated.
            This list can only contain one or both of forecast_reference_time or
            blend_time. The default is ["forecast_reference_time"].

    Returns:
        Updated cubes

    Raises:
        ValueError: if the target_coords list contains anything other than
                    "forecast_reference_time" or "blend_time".
        ValueError: if forecast_reference_time or blend_time is a dimension
                    coordinate.
    """
    result_cubes = iris.cube.CubeList([])

    if not set(target_coords).issubset(set(["forecast_reference_time", "blend_time"])):
        raise ValueError(
            f"Target_coords must be one or both of 'forecast_reference_time' or 'blend_time'. "
            f"Got {target_coords}"
        )

    for cube in cubes:
        cube = cube.copy()
        for target_coord in target_coords:
            new_frt_coord = _create_frt_type_coord(cube, cycletime, name=target_coord)
            cube.remove_coord(new_frt_coord.name())
            cube.add_aux_coord(new_frt_coord, data_dims=None)

        # Update the target_coords for consistency within each cube
        if cube.coords("forecast_period"):
            cube.remove_coord("forecast_period")
        fp_coord = forecast_period_coord(cube, force_lead_time_calculation=True)
        cube.add_aux_coord(fp_coord, data_dims=cube.coord_dims("time"))
        result_cubes.append(cube)
    return result_cubes


def _find_latest_cycletime(cubelist: Union[CubeList, List[Cube]]) -> datetime:
    """
    Find the latest cycletime from the cubes in a cubelist and convert it into
    a datetime object.

    Args:
        cubelist:
            A list of cubes each containing single time step from different
            forecast cycles.

    Returns:
        A datetime object corresponding to the latest forecast reference
        time in the input cubelist.
    """
    # Get cycle time as latest forecast reference time
    if any(cube.coord_dims("forecast_reference_time") for cube in cubelist):
        raise ValueError(
            "Expecting scalar forecast_reference_time for each input "
            "cube - cannot replace a dimension coordinate"
        )

    frt_coord = cubelist[0].coord("forecast_reference_time").copy()
    for cube in cubelist:
        next_coord = cube.coord("forecast_reference_time").copy()
        next_coord.convert_units(frt_coord.units)
        if next_coord.points[0] > frt_coord.points[0]:
            frt_coord = next_coord
    (cycletime,) = frt_coord.units.num2date(frt_coord.points)
    return cycletime
