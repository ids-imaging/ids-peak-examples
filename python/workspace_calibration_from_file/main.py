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

from ids_peak_icv import Image, PointCloud
from ids_peak_icv.calibration import CalibrationParameters, CalibrationPlate, WorkspaceCalibration

DATA_PATH = (
    Path(__file__).resolve().parent / ".." / ".." / "data" / "workspace_calibration_from_file"
).resolve()


def main() -> None:
    # Create a workspace calibration object
    calibration_parameters = CalibrationParameters.create_from_file(
        str(DATA_PATH / "intrinsic_parameters.json")
    )
    calibration_plate = CalibrationPlate.create_from_file(
        str(DATA_PATH / "1012041-radon-checkerboard-marker-65mm-6x6.json")
    )
    workspace_calibration = WorkspaceCalibration.create_from_intrinsics_and_plate(
        calibration_parameters.intrinsic_parameters, calibration_plate
    )

    # Perform the workspace calibration
    image = Image.create_from_file(str(DATA_PATH / "workspace.png"))
    calibration_result = workspace_calibration.process(image)
    print("Mean reprojection error: {:.2f}".format(calibration_result.mean_reprojection_error))

    # Apply the workspace calibration to a point cloud
    point_cloud = PointCloud.create_from_file(str(DATA_PATH / "point_cloud.ply"))
    transformed_point_cloud = point_cloud.transform_to_workspace(
        calibration_result.calibration_parameters.extrinsic_parameters
    )
    # Save the transformed point cloud
    transformed_point_cloud.save("transformed_point_cloud.ply")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
        sys.exit(-1)
