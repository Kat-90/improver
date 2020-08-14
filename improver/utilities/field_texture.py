# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# (C) British Crown Copyright 2017-2020 Met Office.
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
""" Module containing plugin to calculate the texture in a field considering edge transitions."""

import iris
import numpy as np
from iris.exceptions import CoordinateNotFoundError

from improver import BasePlugin
from improver.metadata.constants.attributes import MANDATORY_ATTRIBUTE_DEFAULTS
from improver.metadata.utilities import create_new_diagnostic_cube
from improver.nbhood.square_kernel import SquareNeighbourhood
from improver.threshold import BasicThreshold
from improver.utilities.cube_manipulation import collapsed


class FieldTexture(BasePlugin):
    """Plugin to calculate the texture in a binary field considering edge transitions

    1) Takes a binary field that has been thresholded and looks for the transitions/edges
       in the field that mark out a transition.
    2) The transition calculation is then fed into the neighbourhooding code
       (_calculate_ratio) to calculate a ratio for each cell.
    3) The new cube of ratios is then thresholded and the realization coordinates
       are collapsed to generate a mean of the thresholded ratios.
    """

    def __init__(self, nbhood_radius, ratio_threshold):
        """

        Args:
            nbhood_radius (float):
                The neighbourhood radius in metres within which the number of potential
                transitions should be calculated. This forms the denominator in the
                calculation of the ratio of actual to potential transitions that indicates a
                field's texture. A larger radius should be used for diagnosing larger-scale
                textural features.

            ratio_threshold (float):
                A unit-less threshold value that defines the ratio value above which
                the field is considered clumpy and below which the field is considered
                more contiguous.

        """
        self.nbhood_radius = nbhood_radius
        self.ratio_threshold = ratio_threshold

    def _calculate_ratio(self, cube, radius):
        """
        Calculates the ratio of actual to potential value transitions in a
        neighbourhood about each cell.

        The process is as follows:

            1. For each grid cell find the number of cells of value 1 in a surrounding
               neighbourhood of a size defined by the arg radius. The potential
               transitions within that neighbourhood are defined as the number of
               orthogonal neighbours (up, down, left, right) about cells of value 1.
               This is 4 times the number of cells of value 1.
            2. Calculate the number of actual transitions within the neighbourhood,
               that is the number of cells of value 0 that orthogonally abut cells
               of value 1.
            3. Calculate the ratio of actual to potential transitions.

        Ratios approaching 1 indicate that there are many transitions, so the field
        is highly textured. Ratios close to 0 indicate a smoother field.

        A neighbourhood full of cells of value 1 will return ratios of 0; the
        diagnostic that has been thresholded to produce the binary field is found
        everywhere within that neighbourhood, giving a smooth field. At the other
        extreme, in neighbourhoods in which there are no cells of value 1 the ratio
        is set to 1.

        Args:
            cube (iris.cube.Cube):
                Input data in cube format containing a two-dimensional field
                of binary data.

            radius (float):
                Radius for neighbourhood in metres.

        Returns:
            iris.cube.Cube:
                A ratio between 0 and 1 of actual transitions over potential transitions.
        """
        # Calculate the potential transitions within neighbourhoods
        potential_transitions = SquareNeighbourhood(sum_or_fraction="sum").run(
            cube, radius=radius
        )
        potential_transitions.data = np.where(
            cube.data > 0, potential_transitions.data * 4, 0
        )

        # Calculate the actual transitions for each grid cell of value 1 and
        # store them in a cube.
        actual_transitions = potential_transitions.copy(
            data=self._calculate_transitions(cube.data)
        )

        # Sum the number of actual transitions within the neighbourhood.
        actual_transitions = SquareNeighbourhood(sum_or_fraction="sum").run(
            actual_transitions, radius=radius
        )
        actual_transitions.data = np.where(cube.data > 0, actual_transitions.data, 0)

        # Calulate the ratio of actual to potential transitions
        ratio = np.ones_like(actual_transitions.data)
        np.divide(
            actual_transitions.data,
            potential_transitions.data,
            out=ratio,
            where=(cube.data > 0),
        )

        # Create a new cube to contain the resulting ratio data
        ratio = create_new_diagnostic_cube(
            "cell_edge_differences", 1, cube, MANDATORY_ATTRIBUTE_DEFAULTS, data=ratio,
        )
        return ratio

    @staticmethod
    def _calculate_transitions(data):
        """
        Identifies actual transitions present in a binary field. These transitions
        are defined as the number of cells of value zero that directly neighbour
        cells of value 1. The number of transitions is calculated for all cells
        of value 1. The number of transitions for cells of value 0 is set to 0.

        Args:
            data (numpy.ndarray):
                A NumPy array of the input cube for data manipulation.

        Returns:
            numpy.ndarray:
                A NumPy array containing the transitions for ratio calculation.
        """
        padded_data = np.pad(data, 1, mode="edge")
        diff_x = np.abs(np.diff(padded_data, axis=1))
        diff_y = np.abs(np.diff(padded_data, axis=0))
        cell_sum_x = diff_x[:, 0:-1] + diff_x[:, 1:]
        cell_sum_y = diff_y[0:-1, :] + diff_y[1:, :]
        cell_sum = cell_sum_x[1:-1, :] + cell_sum_y[:, 1:-1]
        cell_sum = np.where(data > 0, cell_sum, 0)
        return cell_sum

    def process(self, cube):
        """
        Calculates a field of texture to use in differentiating solid and
        more scattered features.

        Args:
            cube (iris.cube.Cube):
                Input data in cube format containing the field for which the
                texture is to be assessed.

        Returns:
            iris.cube.Cube:
                A cube containing the mean of the thresholded ratios in cube
                format.
        """

        for cell in cube.data[:, :]:
            if ((cell != 0) & (cell != 1)).any():
                raise ValueError("Incorrect input. Cube should hold binary data only")

        ratios = iris.cube.CubeList()

        try:
            cslices = cube.slices_over("realization")
        except CoordinateNotFoundError:
            cslices = [cube]
        for cslice in cslices:
            ratios.append(self._calculate_ratio(cslice, self.nbhood_radius))
        ratios = ratios.merge_cube()
        thresholded = BasicThreshold(self.ratio_threshold).process(ratios)
        thresholded = iris.util.squeeze(
            collapsed(thresholded, "realization", iris.analysis.MEAN)
        )
        return thresholded