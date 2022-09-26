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
"""
Tests for the phase-change-level CLI
"""

import pytest

from . import acceptance as acc

pytestmark = [pytest.mark.acc, acc.skip_if_kgo_missing]
CLI = acc.cli_name_with_dashes(__file__)
run_cli = acc.run_cli(CLI)


@pytest.mark.parametrize("model_id_attr", (True, False))
@pytest.mark.parametrize(
    "phase_type,kgo_name,horiz_interp",
    [
        ("snow-sleet", "snow_sleet", "True"),
        ("sleet-rain", "sleet_rain", "True"),
        ("hail-rain", "hail_rain", "True"),
        ("sleet-rain", "sleet_rain_unfilled", "False"),
    ],
)
def test_phase_change(tmp_path, phase_type, kgo_name, horiz_interp, model_id_attr):
    """Testing:
        snow/sleet level
        sleet/rain level
        hail/rain level
        sleet/rain level leaving below orography points unfilled.
        Tests are for with and without the provision of the model_id_attr attribute.
    """
    pytest.importorskip("stratify")
    test_dir = acc.kgo_root() / CLI
    kgo_name = "{}_kgo.nc".format(kgo_name)
    output_path = tmp_path / "output.nc"
    input_paths = [
        test_dir / x
        for x in ("wet_bulb_temperature.nc", "wbti.nc", "orog.nc", "land_mask.nc")
    ]
    args = [
        *input_paths,
        "--phase-change",
        phase_type,
        "--horizontal-interpolation",
        horiz_interp,
        "--output",
        output_path,
    ]
    if model_id_attr:
        args += ["--model-id-attr", "mosg__model_configuration"]
        kgo_dir = test_dir / "with_id_attr"
    else:
        kgo_dir = test_dir / "without_id_attr"
    kgo_path = kgo_dir / kgo_name
    run_cli(args)
    acc.compare(output_path, kgo_path)
