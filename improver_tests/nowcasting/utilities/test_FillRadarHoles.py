# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of 'IMPROVER' and is released under the BSD 3-Clause license.
# See LICENSE in the root of the repository for full licensing details.
"""Unit tests for the FillRadarHoles plugin"""

import numpy as np
import pytest
from iris.cube import Cube
from numpy.ma import MaskedArray

from improver.nowcasting.utilities import FillRadarHoles
from improver.synthetic_data.set_up_test_cubes import set_up_variable_cube


@pytest.fixture(name="rainrate")
def rainrate_fixture() -> Cube:
    """Masked rain rates in mm/h"""
    nonzero_data = np.array(
        [
            [0.03, 0.1, 0.1, 0.1, 0.03],
            [0.1, 0.2, 0.2, np.nan, 0.1],
            [0.2, 0.5, np.nan, np.nan, 0.2],
            [0.1, 0.5, np.nan, np.nan, 0.1],
            [0.03, 0.2, 0.2, 0.1, 0.03],
        ]
    )
    data = np.zeros((16, 16), dtype=np.float32)
    data[5:12, 5:12] = np.full((7, 7), 0.03, dtype=np.float32)
    data[6:11, 6:11] = nonzero_data.astype(np.float32)
    mask = np.where(np.isfinite(data), False, True)
    m_data = MaskedArray(data, mask=mask)
    cube = set_up_variable_cube(
        m_data, name="lwe_precipitation_rate", units="mm h-1", spatial_grid="equalarea"
    )
    return cube


@pytest.fixture(name="interp_rainrate")
def interp_rainrate_fixture(rainrate) -> MaskedArray:
    """Interpolated rain rates, expected output from applying FillRadarHoles"""
    data = rainrate.data.copy()
    data[7:10, 8:10] = [
        [0.2, 0.07138586],
        [0.11366593, 0.09165306],
        [0.09488520, 0.07650946],
    ]
    data.mask = np.full_like(data, False)
    return data


def check_fillradarholes(result, expected):
    """Results comparison for test functions"""
    assert isinstance(result, Cube)
    assert isinstance(result.data, MaskedArray)
    np.testing.assert_allclose(result.data, expected.data, rtol=1e-5, atol=1e-8)
    np.testing.assert_array_equal(result.data.mask, expected.mask)


def test_mm_hour(rainrate, interp_rainrate):
    """Test filling radar holes in units of mm/h"""
    plugin = FillRadarHoles()
    result = plugin(rainrate)
    check_fillradarholes(result, interp_rainrate)


def test_metres_sec(rainrate, interp_rainrate):
    """Test filling radar holes in units of m/s"""
    plugin = FillRadarHoles()
    rainrate.convert_units("m s-1")
    result = plugin(rainrate)
    expected = interp_rainrate / (3600.0 * 1000.0)
    check_fillradarholes(result, expected)


def test_wide_mask(rainrate):
    """Test filling radar holes with a widespread mask,
    interpolation should not be triggered in this case"""
    plugin = FillRadarHoles()
    rainrate.data[:11, :11] = np.nan
    rainrate.data.mask = np.where(np.isfinite(rainrate.data.data), False, True)
    result = plugin(rainrate)
    check_fillradarholes(result, rainrate.data.copy())
