# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# (C) British Crown copyright. The Met Office.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Unit tests for the utilities.OccurrenceWithinVicinity plugin."""

import datetime
from typing import Tuple

import numpy as np
import pytest
from iris.cube import Cube
from numpy import ndarray

from improver.synthetic_data.set_up_test_cubes import (
    add_coordinate,
    set_up_variable_cube,
)
from improver.utilities.spatial import OccurrenceWithinVicinity


def land_mask_cube_generator(shape: Tuple[int, int] = (5, 5)) -> Cube:
    """Creates a land-mask cube for use in these tests"""
    mask = np.zeros(shape, dtype=np.int8)
    mask[:, 3:] = 1
    return set_up_variable_cube(
        mask,
        name="land_binary_mask",
        units="1",
        spatial_grid="equalarea",
        grid_spacing=2000.0,
        domain_corner=(0.0, 0.0),
    )


@pytest.fixture
def all_land_cube() -> Cube:
    cube = land_mask_cube_generator((4, 4))
    cube.data = np.zeros_like(cube.data)
    return cube


@pytest.fixture
def land_mask_cube() -> Cube:
    cube = land_mask_cube_generator()
    return cube


@pytest.fixture
def binary_expected() -> ndarray:
    return np.array(
        [
            [1.0, 1.0, 1.0, 0.0, 0.0],
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [0.0, 0.0, 1.0, 1.0, 1.0],
            [0.0, 0.0, 1.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 0.0, 0.0],
        ]
    )


@pytest.fixture
def cube() -> Cube:
    """Sets up a cube for testing"""
    return set_up_variable_cube(
        np.zeros((5, 5), dtype=np.float32),
        spatial_grid="equalarea",
        grid_spacing=2000.0,
        domain_corner=(0.0, 0.0),
    )


@pytest.fixture
def latlon_cube() -> Cube:
    """Sets up a lat-lon cube for testing"""
    return set_up_variable_cube(
        np.zeros((5, 5), dtype=np.float32),
        spatial_grid="latlon",
        grid_spacing=1.0,
        domain_corner=(0.0, 0.0),
    )


RADIUS = 2000
GRID_POINT_RADIUS = 1


@pytest.mark.parametrize(
    "kwargs", ({"radius": RADIUS}, {"grid_point_radius": GRID_POINT_RADIUS})
)
def test_basic(cube, binary_expected, kwargs):
    """Test for binary events to determine where there is an occurrence
    within the vicinity."""

    cube.data[0, 1] = 1.0
    cube.data[2, 3] = 1.0
    result = OccurrenceWithinVicinity(**kwargs).maximum_within_vicinity(cube)
    assert isinstance(result, Cube)
    assert np.allclose(result.data, binary_expected)


def test_basic_latlon(latlon_cube, binary_expected):
    """Test for occurrence in vicinity calculation on a lat-lon (non equal
    area) grid using a grid_point_radius."""

    latlon_cube.data[0, 1] = 1.0
    latlon_cube.data[2, 3] = 1.0
    result = OccurrenceWithinVicinity(
        grid_point_radius=GRID_POINT_RADIUS
    ).maximum_within_vicinity(latlon_cube)
    assert isinstance(result, Cube)
    assert np.allclose(result.data, binary_expected)


@pytest.mark.parametrize("fixture_name", ["cube", "latlon_cube"])
@pytest.mark.parametrize("keyword", ["radius", "grid_point_radius"])
@pytest.mark.parametrize("value", [0, None])
def test_zero_radius(request, fixture_name, keyword, value):
    """Test that if a zero radius / grid point radius, or no radius / grid point
    radius is provided, the input data is returned unchanged. This test uses
    both an equal area and latlon grid as a 0 radius can be applied to both."""
    cube = request.getfixturevalue(fixture_name)
    kwargs = {keyword: value}
    expected = cube.data.copy()
    result = OccurrenceWithinVicinity(**kwargs).maximum_within_vicinity(cube)
    assert np.allclose(result.data, expected)


def test_fuzzy(cube):
    """Test for non-binary events to determine where there is an occurrence
    within the vicinity."""
    expected = np.array(
        [
            [1.0, 1.0, 1.0, 0.0, 0.0],
            [1.0, 1.0, 1.0, 0.5, 0.5],
            [0.0, 0.0, 0.5, 0.5, 0.5],
            [0.0, 0.0, 0.5, 0.5, 0.5],
            [0.0, 0.0, 0.0, 0.0, 0.0],
        ]
    )
    cube.data[0, 1] = 1.0
    cube.data[2, 3] = 0.5
    result = OccurrenceWithinVicinity(radius=RADIUS).maximum_within_vicinity(cube)
    assert isinstance(result, Cube)
    assert np.allclose(result.data, expected)


@pytest.mark.parametrize(
    "kwargs", ({"radius": 2 * RADIUS}, {"grid_point_radius": 2 * GRID_POINT_RADIUS})
)
def test_different_distance(cube, kwargs):
    """Test for binary events to determine where there is an occurrence
    within the vicinity for an alternative distance."""
    expected = np.array(
        [
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0, 1.0, 1.0],
        ]
    )
    cube.data[0, 1] = 1.0
    cube.data[2, 3] = 1.0
    result = OccurrenceWithinVicinity(**kwargs).maximum_within_vicinity(cube)
    assert isinstance(result, Cube)
    assert np.allclose(result.data, expected)


def test_masked_data(cube):
    """Test masked values are ignored in OccurrenceWithinVicinity."""
    expected = np.array(
        [
            [1.0, 1.0, 1.0, 0.0, 10.0],
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [0.0, 0.0, 1.0, 1.0, 1.0],
            [0.0, 0.0, 1.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 0.0, 0.0],
        ]
    )
    cube.data[0, 1] = 1.0
    cube.data[2, 3] = 1.0
    cube.data[0, 4] = 10.0
    mask = np.zeros((5, 5))
    mask[0, 4] = 1
    cube.data = np.ma.array(cube.data, mask=mask)
    result = OccurrenceWithinVicinity(radius=RADIUS).maximum_within_vicinity(cube)
    assert isinstance(result, Cube)
    assert isinstance(result.data, np.ma.core.MaskedArray)
    assert np.allclose(result.data.data, expected)
    assert np.allclose(result.data.mask, mask)


def test_with_land_mask(cube, land_mask_cube):
    """Test that a land mask is used correctly."""
    expected = np.array(
        [
            [1.0, 1.0, 1.0, 10.0, 10.0],
            [1.0, 1.0, 1.0, 10.0, 10.0],
            [0.0, 0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 0.0, 0.0],
        ]
    )
    cube.data[0, 1] = 1.0  # would not cross mask
    cube.data[2, 3] = 1.0  # would cross mask
    cube.data[0, 4] = 10.0  # would not cross mask
    result = OccurrenceWithinVicinity(
        radius=RADIUS, land_mask_cube=land_mask_cube
    ).maximum_within_vicinity(cube)
    assert isinstance(result, Cube)
    assert ~isinstance(result.data, np.ma.core.MaskedArray)
    assert np.allclose(result.data, expected)


def test_with_land_mask_and_mask(cube, land_mask_cube):
    """Test that a land mask is used correctly when cube also has a mask."""
    expected = np.array(
        [
            [1.0, 1.0, 1.0, 0.0, 10.0],
            [1.0, 1.0, 1.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0, 0.0, 0.0],
        ]
    )
    cube.data[0, 1] = 1.0  # would not cross mask
    cube.data[2, 3] = 1.0  # would cross mask
    cube.data[0, 4] = 10.0  # is masked in input
    mask = np.zeros((5, 5))
    mask[0, 4] = 1
    cube.data = np.ma.array(cube.data, mask=mask)
    result = OccurrenceWithinVicinity(
        RADIUS, land_mask_cube=land_mask_cube
    ).maximum_within_vicinity(cube)
    assert isinstance(result, Cube)
    assert isinstance(result.data, np.ma.core.MaskedArray)
    assert np.allclose(result.data.data, expected)
    assert np.allclose(result.data.mask, mask)


def test_with_invalid_land_mask_name(land_mask_cube):
    """Test that a mis-named land mask is rejected correctly."""
    bad_mask_cube = land_mask_cube.copy()
    bad_mask_cube.rename("kittens")
    with pytest.raises(
        ValueError,
        match="Expected land_mask_cube to be called land_binary_mask, not kittens",
    ):
        OccurrenceWithinVicinity(radius=RADIUS, land_mask_cube=bad_mask_cube)


def test_with_invalid_land_mask_coords(cube, land_mask_cube):
    """Test that a spatially mis-matched land mask is rejected correctly."""
    bad_mask_cube = land_mask_cube.copy()
    bad_points = np.array(bad_mask_cube.coord(axis="x").points)
    bad_points[0] += 1
    bad_mask_cube.coord(axis="x").points = bad_points
    with pytest.raises(
        ValueError,
        match="Supplied cube do not have the same spatial coordinates and land mask",
    ):
        OccurrenceWithinVicinity(radius=RADIUS, land_mask_cube=bad_mask_cube)(cube)


@pytest.fixture(name="cube_with_realizations")
def cube_with_realizations_fixture() -> Cube:
    return set_up_variable_cube(
        np.zeros((2, 4, 4), dtype=np.float32),
        "lwe_precipitation_rate",
        "m s-1",
        "equalarea",
        grid_spacing=2000.0,
        domain_corner=(0.0, 0.0),
    )


TIMESTEPS = [
    datetime.datetime(2017, 11, 9, 12),
    datetime.datetime(2017, 11, 9, 15),
]


@pytest.mark.parametrize("land_fixture", [None, "all_land_cube"])
def test_with_multiple_realizations_and_times(
    request, cube_with_realizations, land_fixture
):
    """Test for multiple realizations and times, so that multiple
    iterations will be required within the process method."""
    cube = cube_with_realizations
    land = request.getfixturevalue(land_fixture) if land_fixture else None
    expected = np.array(
        [
            [
                [
                    [0.0, 0.0, 0.0, 0.0],
                    [1.0, 1.0, 1.0, 0.0],
                    [1.0, 1.0, 1.0, 0.0],
                    [1.0, 1.0, 1.0, 0.0],
                ],
                [
                    [0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                ],
            ],
            [
                [
                    [0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                    [0.0, 0.0, 0.0, 0.0],
                ],
                [
                    [0.0, 0.0, 1.0, 1.0],
                    [0.0, 0.0, 1.0, 1.0],
                    [0.0, 0.0, 1.0, 1.0],
                    [0.0, 0.0, 0.0, 0.0],
                ],
            ],
        ]
    )
    cube = add_coordinate(
        cube, TIMESTEPS, "time", order=[1, 0, 2, 3], is_datetime=True,
    )
    cube.data[0, 0, 2, 1] = 1.0
    cube.data[1, 1, 1, 3] = 1.0
    orig_shape = cube.data.copy().shape
    result = OccurrenceWithinVicinity(radius=RADIUS, land_mask_cube=land)(cube)
    assert isinstance(result, Cube)
    assert result.data.shape == orig_shape
    assert np.allclose(result.data, expected)


@pytest.mark.parametrize("land_fixture", [None, "all_land_cube"])
def test_with_multiple_realizations(request, cube_with_realizations, land_fixture):
    """Test for multiple realizations, so that multiple
    iterations will be required within the process method."""
    cube = cube_with_realizations
    land = request.getfixturevalue(land_fixture) if land_fixture else None
    expected = np.array(
        [
            [
                [0.0, 0.0, 0.0, 0.0],
                [1.0, 1.0, 1.0, 0.0],
                [1.0, 1.0, 1.0, 0.0],
                [1.0, 1.0, 1.0, 0.0],
            ],
            [
                [0.0, 0.0, 1.0, 1.0],
                [0.0, 0.0, 1.0, 1.0],
                [0.0, 0.0, 1.0, 1.0],
                [0.0, 0.0, 0.0, 0.0],
            ],
        ]
    )
    cube.data[0, 2, 1] = 1.0
    cube.data[1, 1, 3] = 1.0
    result = OccurrenceWithinVicinity(radius=RADIUS, land_mask_cube=land)(cube)
    assert isinstance(result, Cube)
    assert np.allclose(result.data, expected)


@pytest.mark.parametrize("land_fixture", [None, "all_land_cube"])
def test_with_multiple_times(request, cube_with_realizations, land_fixture):
    """Test for multiple times, so that multiple
    iterations will be required within the process method."""
    cube = cube_with_realizations
    land = request.getfixturevalue(land_fixture) if land_fixture else None
    expected = np.array(
        [
            [
                [0.0, 0.0, 0.0, 0.0],
                [1.0, 1.0, 1.0, 0.0],
                [1.0, 1.0, 1.0, 0.0],
                [1.0, 1.0, 1.0, 0.0],
            ],
            [
                [0.0, 0.0, 1.0, 1.0],
                [0.0, 0.0, 1.0, 1.0],
                [0.0, 0.0, 1.0, 1.0],
                [0.0, 0.0, 0.0, 0.0],
            ],
        ]
    )
    cube = cube[0]
    cube = add_coordinate(cube, TIMESTEPS, "time", is_datetime=True,)
    cube.data[0, 2, 1] = 1.0
    cube.data[1, 1, 3] = 1.0
    orig_shape = cube.data.shape
    result = OccurrenceWithinVicinity(radius=RADIUS, land_mask_cube=land)(cube)
    assert isinstance(result, Cube)
    assert result.data.shape == orig_shape
    assert np.allclose(result.data, expected)


@pytest.mark.parametrize("land_fixture", [None, "all_land_cube"])
def test_no_realization_or_time(request, cube_with_realizations, land_fixture):
    """Test for no realizations and no times, so that the iterations
    will not require slicing cubes within the process method."""
    cube = cube_with_realizations
    land = request.getfixturevalue(land_fixture) if land_fixture else None
    expected = np.array(
        [
            [0.0, 0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0, 0.0],
            [1.0, 1.0, 1.0, 0.0],
            [1.0, 1.0, 1.0, 0.0],
        ]
    )
    cube = cube[0]
    cube.data[2, 1] = 1.0
    orig_shape = cube.data.shape
    result = OccurrenceWithinVicinity(radius=RADIUS, land_mask_cube=land)(cube)
    assert isinstance(result, Cube)
    assert result.data.shape == orig_shape
    assert np.allclose(result.data, expected)


@pytest.mark.parametrize("radius", [0, 2000])
def test_two_radii_provided_exception(cube, radius):
    """Test an exception is raised if both radius and grid_point_radius are
    provided as arguments."""
    with pytest.raises(
        ValueError, match="Only one of radius or grid_point_radius should be set"
    ):
        OccurrenceWithinVicinity(radius=radius, grid_point_radius=2)
