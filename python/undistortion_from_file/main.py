# Copyright (C) 2026, IDS Imaging Development Systems GmbH.
#
# Permission to use, copy, modify, and/or distribute this software for
# any purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
# FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
# AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


import sys
from pathlib import Path

from ids_peak_icv import Image
from ids_peak_icv.calibration import CalibrationParameters
from ids_peak_icv.transformations import Undistortion

DATA_PATH = (
    Path(__file__).resolve().parent / ".." / ".." / "data" / "undistortion_from_file"
).resolve()


def main() -> None:
    calibration_parameters_path = str(DATA_PATH / "calibration_parameters.json")
    input_image_path = str(DATA_PATH / "fisheye.png")

    print("Loading input image from", input_image_path)
    input_image = Image.create_from_file(input_image_path)

    print("Loading calibration parameters from", calibration_parameters_path)
    calibration_parameters = CalibrationParameters.create_from_file(calibration_parameters_path)

    print("Initialize undistortion")
    undistortion = Undistortion.create_from_intrinsics(calibration_parameters.intrinsic_parameters)

    print("Process undistortion")
    output_image = undistortion.process(input_image)

    print("Save undistorted image")
    output_image.save("undistorted_image.png")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
        sys.exit(-1)
