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

from ids_peak_common import PixelFormat
from ids_peak_icv import Image, ICVException, XYZImage, PointCloud
from ids_peak_icv.calibration import CalibrationParameters
from ids_peak_icv.experimental.transformations import XYZProjection
from ids_peak_icv.transformations import Undistortion

DATA_PATH = (
        Path(__file__).resolve().parent / ".." / ".." / "data" / "textured_pointcloud_from_file"
).resolve()


def main() -> None:
    try:
        camera_3d_path = DATA_PATH / "3d_camera"
        camera_3d_depth_map_path = str(camera_3d_path / "depth_map.tiff")
        camera_3d_calibration_parameters_path = str(camera_3d_path / "calibration_parameters.json")

        camera_2d_path = DATA_PATH / "2d_camera"
        camera_2d_image_path = str(camera_2d_path / "color_image.png")
        camera_2d_calibration_parameters_path = str(camera_2d_path / "calibration_parameters.json")

        camera_3d_depth_map = Image.create_from_file(camera_3d_depth_map_path, PixelFormat.COORD3D_C32F)
        camera_2d_image = Image.create_from_file(camera_2d_image_path)

        camera_3d_calibration_parameters = CalibrationParameters.create_from_file(camera_3d_calibration_parameters_path)
        camera_2d_calibration_parameters = CalibrationParameters.create_from_file(camera_2d_calibration_parameters_path)

        undistortion = Undistortion.create_from_intrinsics(camera_3d_calibration_parameters.intrinsic_parameters)
        camera_3d_undistorted_depth_map = undistortion.process(camera_3d_depth_map)
        camera_3d_xyz_image = XYZImage.create_from_undistorted_image(camera_3d_undistorted_depth_map)

        projection = XYZProjection.create_from_extrinsics_and_calibration_parameters(
            camera_3d_calibration_parameters.extrinsic_parameters,
            camera_2d_calibration_parameters
        )

        # Rearrange every point in the xyz image
        # to its corresponding 2d color pixel
        # to ensure 1:1 pixel index alignment
        # between depth and color data.
        camera_3d_projected_xyz_image = projection.process(camera_3d_xyz_image)

        point_cloud = PointCloud.create_from_xyz_image(camera_3d_projected_xyz_image, camera_2d_image)

        output_file_path = "textured_pointcloud.ply"

        point_cloud.save(output_file_path)
        print("Point cloud saved to", output_file_path)

    except ICVException as e:
        print(e)
        sys.exit(e.status.value)
    except Exception as e:
        print(e)
        sys.exit(-1)


if __name__ == "__main__":
    main()
