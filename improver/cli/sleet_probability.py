#!/usr/bin/env python
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
"""Script to calculate sleet probability."""

from improver import cli


@cli.clizefy
@cli.with_output
def process(*cubes: cli.inputcube):
    """Calculate sleet probability.

    Calculates the sleet probability using the
    calculate_sleet_probability plugin.

    Args:
        cubes (iris.cube.CubeList or list of iris.cube.Cube):
            containing, in any order:
                snow (iris.cube.Cube):
                    An iris Cube of the probability of snow.
                rain (iris.cube.Cube):
                    An iris Cube of the probability of rain.

    Returns:
        iris.cube.Cube:
            Returns a cube with the probability of sleet.
    """

    from iris.cube import CubeList

    from improver.precipitation_type.calculate_sleet_prob import (
        calculate_sleet_probability,
    )

    snow, rain = CubeList(cubes).extract(
        ["probability_of_snow_at_surface", "probability_of_rain_at_surface"]
    )

    return calculate_sleet_probability(snow, rain)
