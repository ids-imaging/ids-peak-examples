/*
 * Copyright (C) 2026, IDS Imaging Development Systems GmbH.
 *
 * Permission to use, copy, modify, and/or distribute this software for
 * any purpose with or without fee is hereby granted.
 *
 * THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
 * WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
 * FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
 * DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
 * AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
 * OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

#include <iostream>
#include <string>

#include <peak_icv/peak_icv.hpp>
#include <peak_icv/algorithms/transformations/peak_icv_xyz_projection.hpp>

#ifndef DATA_PATH
#    error "Define DATA_PATH to the examples data folder"
#endif

int main()
{
    try
    {
        peak::icv::library::Init();

        const std::string texturedPointCloudDataPath = DATA_PATH "/textured_pointcloud_from_file";

        const std::string camera3dPath = texturedPointCloudDataPath + "/3d_camera";
        const std::string camera3dDepthMapPath = camera3dPath + "/depth_map.tiff";
        const std::string camera3dCalibrationParametersPath = camera3dPath + "/calibration_parameters.json";

        const std::string camera2dPath = texturedPointCloudDataPath + "/2d_camera";
        const std::string camera2dImagePath = camera2dPath + "/color_image.png";
        const std::string camera2dCalibrationParametersPath = camera2dPath + "/calibration_parameters.json";

        const peak::icv::Image camera3dDepthMap(
            camera3dDepthMapPath, peak::common::PixelFormat::Coord3D_C32f);
        auto camera2dImage = peak::icv::Image(camera2dImagePath);

        auto camera3dCalibrationParameters = peak::icv::CalibrationParameters(
            camera3dCalibrationParametersPath);
        auto camera2dCalibrationParameters = peak::icv::CalibrationParameters(
            camera2dCalibrationParametersPath);

        auto undistortion = peak::icv::Undistortion(
            camera3dCalibrationParameters.GetIntrinsicParameters()
        );
        auto camera3dUndistortedDepthMap = undistortion.Process(camera3dDepthMap);

        auto camera3dXyzImage = peak::icv::XYZImage(camera3dUndistortedDepthMap);

        auto projection =
            peak::icv::experimental::XYZProjection(
                camera3dCalibrationParameters.GetExtrinsicParameters(),
                camera2dCalibrationParameters
            );

        // Rearrange every point in the xyz image
        // to its corresponding 2d color pixel
        // to ensure 1:1 pixel index alignment
        // between depth and color data.
        auto camera3dProjectedXyzImage = projection.Process(camera3dXyzImage);

        auto pointCloud = peak::icv::PointCloudXYZRGB(camera3dProjectedXyzImage, camera2dImage);

        std::string outputFilePath = "textured_pointcloud.ply";

        peak::icv::PointCloudWriter pointCloudWriter;
        pointCloudWriter.Write(outputFilePath, pointCloud);

        std::cout << "Point cloud saved to " << outputFilePath << std::endl;

        peak::icv::library::Exit();
    }
    catch (const peak::icv::Exception& e)
    {
        std::cerr << "ICV Exception: " << e.what() << std::endl;
        return static_cast<int>(e.GetStatus());
    }
    catch (const std::exception& e)
    {
        std::cerr << "Exception: " << e.what() << std::endl;
        return -1;
    }


    return 0;
}
