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
from typing import Tuple

from ids_peak_common import PixelFormat
from ids_peak_icv import Image, PointCloud
from ids_peak_icv.calibration import CalibrationParameters
from ids_peak_icv.transformations import Undistortion

DATA_PATH = (
    Path(__file__).resolve().parent / ".." / ".." / "data" / "point_cloud_from_file"
).resolve()


def load_files() -> Tuple[Image, Image, CalibrationParameters]:
    print("Read depth map from file")
    depth_map = Image.create_from_file(
        str(DATA_PATH / "depth_map.tiff"),
        PixelFormat.COORD3D_C32F,
    )

    print("Read calibration result from file")
    calibration_parameters = CalibrationParameters.create_from_file(
        str(DATA_PATH / "calibration_parameters.json")
    )

    print("Read intensity image from file")
    intensity_image = Image.create_from_file(str(DATA_PATH / "intensity.png"))

    return depth_map, intensity_image, calibration_parameters


def main() -> None:
    depth_map, intensity_image, calibration_parameters = load_files()

    undistortion = Undistortion.create_from_intrinsics(calibration_parameters.intrinsic_parameters)
    undistorted_depth_map = undistortion.process(depth_map)
    undistorted_intensity_image = undistortion.process(intensity_image)

    print("Create and save point cloud")
    point_cloud = PointCloud.create_from_undistorted_depth_map(
        undistorted_depth_map, undistorted_intensity_image
    )
    point_cloud.save("point_cloud.ply")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
        sys.exit(-1)
