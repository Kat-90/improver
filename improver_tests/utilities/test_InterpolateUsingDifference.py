# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of 'IMPROVER' and is released under the BSD 3-Clause license.
# See LICENSE in the root of the repository for full licensing details.
"""Unit tests for the InterpolateUsingDifference plugin."""

import unittest
from unittest.mock import patch, sentinel

import numpy as np
import pytest
from numpy.testing import assert_array_almost_equal, assert_array_equal

from improver.synthetic_data.set_up_test_cubes import (
    add_coordinate,
    set_up_variable_cube,
)
from improver.utilities.interpolation import InterpolateUsingDifference


class HaltExecution(Exception):
    pass


@patch("improver.utilities.interpolation.as_cube")
def test_as_cube_called(mock_as_cube):
    mock_as_cube.side_effect = [None, None, HaltExecution]  # halt execution on 2nd call
    try:
        InterpolateUsingDifference()(
            sentinel.cube, sentinel.reference_cube, limit=sentinel.limit_cube
        )
    except HaltExecution:
        pass
    mock_as_cube.assert_any_call(sentinel.cube)
    mock_as_cube.assert_any_call(sentinel.limit_cube)
    mock_as_cube.assert_any_call(sentinel.reference_cube)


class Test_Setup(unittest.TestCase):
    """Set up for InterpolateUsingDifference tests."""

    def setUp(self):
        """Set up arrays for testing."""
        snow_sleet = np.array(
            [[5.0, 5.0, 5.0], [10.0, 10.0, 10.0], [5.0, 5.0, 5.0]], dtype=np.float32
        )
        sleet_rain = np.array(
            [[4.0, 4.0, 4.0], [np.nan, np.nan, np.nan], [3.0, 3.0, 3.0]],
            dtype=np.float32,
        )
        sleet_rain = np.ma.masked_invalid(sleet_rain)
        limit_data = np.array(
            [[4.0, 4.0, 4.0], [10.0, 8.0, 6.0], [4.0, 4.0, 4.0]], dtype=np.float32
        )

        self.snow_sleet = set_up_variable_cube(
            snow_sleet,
            name="altitude_of_snow_falling_level",
            units="m",
            spatial_grid="equalarea",
        )
        self.sleet_rain = set_up_variable_cube(
            sleet_rain,
            name="altitude_of_rain_falling_level",
            units="m",
            spatial_grid="equalarea",
        )
        self.limit = set_up_variable_cube(
            limit_data, name="surface_altitude", units="m", spatial_grid="equalarea"
        )


class Test_repr(unittest.TestCase):
    """Test the InterpolateUsingDifference __repr__ method."""

    def test_basic(self):
        """Test expected string representation is returned."""
        self.assertEqual(
            str(InterpolateUsingDifference()), "<InterpolateUsingDifference>"
        )


class Test_process_check_inputs(Test_Setup):
    """Tests for input check behaviour of process method."""

    def test_incomplete_reference_data(self):
        """Test an exception is raised if the reference field is incomplete."""

        self.snow_sleet.data[1, 1] = np.nan
        msg = "The reference cube contains np.nan data"
        with self.assertRaisesRegex(ValueError, msg):
            InterpolateUsingDifference().process(self.sleet_rain, self.snow_sleet)

    def test_incompatible_reference_cube_units(self):
        """Test an exception is raised if the reference cube has units that
        are incompatible with the input cube."""

        self.snow_sleet.units = "s"
        msg = "Reference cube and/or limit do not have units compatible"
        with self.assertRaisesRegex(ValueError, msg):
            InterpolateUsingDifference().process(self.sleet_rain, self.snow_sleet)

    def test_incompatible_limit_units(self):
        """Test an exception is raised if the limit cube has units that
        are incompatible with the input cube."""

        self.limit.units = "s"
        msg = "Reference cube and/or limit do not have units compatible"
        with self.assertRaisesRegex(ValueError, msg):
            InterpolateUsingDifference().process(
                self.sleet_rain, self.snow_sleet, limit=self.limit
            )

    def test_convert_units(self):
        """Test that a reference cube and limit cube with different but
        compatible units are converted without an exception being raised."""

        self.snow_sleet.convert_units("cm")
        self.limit.convert_units("cm")

        InterpolateUsingDifference().process(
            self.sleet_rain, self.snow_sleet, limit=self.limit
        )


class Test_process(Test_Setup):
    """Test the InterpolateUsingDifference process method."""

    def test_unlimited(self):
        """Test interpolation to complete an incomplete field using a reference
        field. No limit is imposed upon the returned interpolated values."""

        expected = np.array(
            [[4.0, 4.0, 4.0], [8.5, 8.5, 8.5], [3.0, 3.0, 3.0]], dtype=np.float32
        )

        result = InterpolateUsingDifference().process(self.sleet_rain, self.snow_sleet)

        assert_array_equal(result.data, expected)
        self.assertEqual(result.coords(), self.sleet_rain.coords())
        self.assertEqual(result.metadata, self.sleet_rain.metadata)

    def test_maximum_limited(self):
        """Test interpolation to complete an incomplete field using a reference
        field. A limit is imposed upon the returned interpolated values,
        forcing these values to the maximum limit if they exceed it."""

        expected = np.array(
            [[4.0, 4.0, 4.0], [8.5, 8.0, 6.0], [3.0, 3.0, 3.0]], dtype=np.float32
        )

        result = InterpolateUsingDifference(limit_as_maximum=True).process(
            self.sleet_rain, self.snow_sleet, limit=self.limit
        )

        assert_array_equal(result.data, expected)
        self.assertEqual(result.coords(), self.sleet_rain.coords())
        self.assertEqual(result.metadata, self.sleet_rain.metadata)

    def test_minimum_limited(self):
        """Test interpolation to complete an incomplete field using a reference
        field. A limit is imposed upon the returned interpolated values,
        forcing these values to the minimum limit if they are below it."""

        expected = np.array(
            [[4.0, 4.0, 4.0], [10.0, 8.5, 8.5], [3.0, 3.0, 3.0]], dtype=np.float32
        )

        result = InterpolateUsingDifference(limit_as_maximum=False).process(
            self.sleet_rain, self.snow_sleet, limit=self.limit
        )

        assert_array_equal(result.data, expected)
        self.assertEqual(result.coords(), self.sleet_rain.coords())
        self.assertEqual(result.metadata, self.sleet_rain.metadata)

    def test_multi_realization_limited(self):
        """Test interpolation to complete an incomplete field using a reference
        field. A limit is imposed upon the returned interpolated values,
        forcing these values to the minimum limit if they are below it. The
        inputs are multi-realization."""

        snow_sleet = add_coordinate(self.snow_sleet, [0, 1], "realization")
        sleet_rain = add_coordinate(self.sleet_rain, [0, 1], "realization")

        expected = np.array(
            [[4.0, 4.0, 4.0], [10.0, 8.5, 8.5], [3.0, 3.0, 3.0]], dtype=np.float32
        )

        result = InterpolateUsingDifference(limit_as_maximum=False).process(
            sleet_rain, snow_sleet, limit=self.limit
        )

        assert_array_equal(result[0].data, expected)
        assert_array_equal(result[1].data, expected)
        self.assertEqual(result.shape, sleet_rain.shape)
        self.assertEqual(result.coords(), sleet_rain.coords())
        self.assertEqual(result.metadata, sleet_rain.metadata)

    def test_crossing_values(self):
        """Test interpolation when the reference field and field to be
        completed by interpolation cross one another. In the absence of any
        limit it should be possible to return an interpolated field of values
        that pass through the reference field in an expected way. In another
        case we apply the reference field as a lower bound to the interpolated
        values."""

        snow_sleet = np.array(
            [[15.0, 15.0, 15.0], [10.0, 10.0, 10.0], [8.0, 8.0, 8.0]], dtype=np.float32
        )

        sleet_rain = np.array(
            [[5.0, 5.0, 5.0], [np.nan, np.nan, np.nan], [15.0, 15.0, 15.0]],
            dtype=np.float32,
        )
        sleet_rain = np.ma.masked_invalid(sleet_rain)

        self.snow_sleet.data = snow_sleet
        self.sleet_rain.data = sleet_rain

        expected_unlimited = np.array(
            [[5.0, 5.0, 5.0], [8.5, 8.5, 8.5], [15.0, 15.0, 15.0]], dtype=np.float32
        )
        expected_limited = np.array(
            [[5.0, 5.0, 5.0], [10.0, 10.0, 10.0], [15.0, 15.0, 15.0]], dtype=np.float32
        )

        result_unlimited = InterpolateUsingDifference().process(
            self.sleet_rain, self.snow_sleet
        )

        result_limited = InterpolateUsingDifference(limit_as_maximum=False).process(
            self.sleet_rain, self.snow_sleet, limit=self.snow_sleet
        )

        assert_array_equal(result_unlimited.data, expected_unlimited)
        assert_array_equal(result_limited.data, expected_limited)

    def test_linear_failure(self):
        """Test that if the use of linear interpolation does not result in a
        complete difference field, and thus a complete field of interest, the
        secondary use of nearest neighbour interpolation completes the
        field."""

        sleet_rain = np.array(
            [[np.nan, np.nan, 4.0], [np.nan, np.nan, np.nan], [3.0, 3.0, 3.0]],
            dtype=np.float32,
        )
        sleet_rain = np.ma.masked_invalid(sleet_rain)
        self.sleet_rain.data = sleet_rain

        expected = np.array(
            [[3.5, 4.0, 4.0], [8.5, 8.5, 8.5], [3.0, 3.0, 3.0]], dtype=np.float32
        )

        result = InterpolateUsingDifference().process(self.sleet_rain, self.snow_sleet)

        assert_array_equal(result.data, expected)
        self.assertEqual(result.coords(), self.sleet_rain.coords())
        self.assertEqual(result.metadata, self.sleet_rain.metadata)

    def test_unmasked_input_cube(self):
        """Test a warning is raised if the input cube is not masked and that
        the input cube is returned unchanged."""

        self.sleet_rain.data = np.ones((3, 3), dtype=np.float32)
        expected = self.sleet_rain.copy()
        warning_msg = "Input cube unmasked, no data to fill in, returning"

        with pytest.warns(UserWarning, match=warning_msg):
            result = InterpolateUsingDifference().process(
                self.sleet_rain, self.snow_sleet
            )

        self.assertEqual(result, expected)

    def test_convert_units(self):
        """Test that a reference cube and limit cube with different but
        compatible units are converted for use and return the expected
        result."""

        expected = np.array(
            [[4.0, 4.0, 4.0], [8.5, 8.0, 6.0], [3.0, 3.0, 3.0]], dtype=np.float32
        )

        self.snow_sleet.convert_units("cm")
        self.limit.convert_units("cm")

        result = InterpolateUsingDifference().process(
            self.sleet_rain, self.snow_sleet, limit=self.limit
        )

        assert_array_equal(result.data, expected)
        self.assertEqual(result.coords(), self.sleet_rain.coords())
        self.assertEqual(result.metadata, self.sleet_rain.metadata)

    def test_range_enforcement(self):
        """Test interpolation on a case where the result is known to be outside of the
        input data range."""
        data = np.zeros(
            (18, 18), dtype=np.float32
        )  # The smallest array where this behaviour has been found
        data[1:-1, 1:-1] = np.nan
        data[0, 4] = 100
        sleet_rain = np.ma.masked_invalid(data)

        self.snow_sleet = set_up_variable_cube(
            np.zeros_like(data),
            name="altitude_of_snow_falling_level",
            units="m",
            spatial_grid="equalarea",
        )
        self.sleet_rain = set_up_variable_cube(
            sleet_rain,
            name="altitude_of_rain_falling_level",
            units="m",
            spatial_grid="equalarea",
        )

        expected = np.zeros_like(data)
        expected[0, 4] = 100
        expected[1, 3] = 75
        expected[2, 2] = 50
        expected[3, 1] = 25

        result = InterpolateUsingDifference().process(self.sleet_rain, self.snow_sleet)

        assert_array_almost_equal(result.data, expected, decimal=5)
        assert (result.data >= np.nanmin(self.sleet_rain.data)).all()
        assert (result.data <= np.nanmax(self.sleet_rain.data)).all()


if __name__ == "__main__":
    unittest.main()
