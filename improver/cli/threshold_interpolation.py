#!/usr/bin/env python
# (C) Crown Copyright, Met Office. All rights reserved.
#
# This file is part of 'IMPROVER' and is released under the BSD 3-Clause license.
# See LICENSE in the root of the repository for full licensing details.
"""Script to run the threshold interpolation plugin."""

from improver import cli


@cli.clizefy
@cli.with_output
def process(
    forecast_at_thresholds: cli.inputcube,
    *,
    no_of_thresholds: int = None,
    sampling: str = "quantile",
    thresholds: cli.comma_separated_list = None,
):
    """
    1. Creates a list of thresholds, if not provided.
    2. Interpolate the threshold coordinate into an alternative
       set of thresholds using linear interpolation.

    Args:
        forecast_at_thresholds:
            Cube expected to contain a threshold coordinate.
        no_of_thresholds:
            Number of thresholds
            If None, the number of thresholds within the input
            forecast_at_thresholds cube is used as the
            number of thresholds.
        thresholds:
            List of the desired output thresholds.

    Returns:
        Cube with forecast values at the desired set of thresholds.
        The threshold coordinate is always the zeroth dimension.
    """
    from improver.utilities.threshold_interpolation import Threshold_interpolation

    result = Threshold_interpolation(forecast_at_thresholds, no_of_thresholds=no_of_thresholds,
                                     sampling=sampling, thresholds=thresholds,
                                     )
    return result
