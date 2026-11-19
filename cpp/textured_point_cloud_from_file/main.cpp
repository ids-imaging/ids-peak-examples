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

        const peak::icv::Image camera3dDepthMap(camera3dDepthMapPath, peak::common::PixelFormat::Coord3D_C32f);
        const peak::icv::Image camera2dImage(camera2dImagePath);

        const peak::icv::CalibrationParameters camera3dCalibrationParameters(camera3dCalibrationParametersPath);
        const peak::icv::CalibrationParameters camera2dCalibrationParameters(camera2dCalibrationParametersPath);

        peak::icv::Undistortion undistortion(camera3dCalibrationParameters.GetIntrinsicParameters());
        auto camera3dUndistortedDepthMap = undistortion.Process(camera3dDepthMap);

        const peak::icv::XYZImage camera3dXyzImage(camera3dUndistortedDepthMap);

        // Calculate the relative pose between the 3D camera and the 2D camera
        auto pose = peak::icv::experimental::XYZTextureAlignment::CalculateRelativePose(
            camera2dCalibrationParameters.GetExtrinsicParameters(),
            camera3dCalibrationParameters.GetExtrinsicParameters());

        peak::icv::experimental::XYZTextureAlignment alignment(
            pose, camera2dCalibrationParameters.GetIntrinsicParameters());

        // Rearrange every point in the xyz image
        // to its corresponding 2d color pixel
        // to ensure 1:1 pixel index alignment
        // between depth and color data.
        auto camera3dProjectedXyzImage = alignment.AlignXYZToTextureGrid(camera3dXyzImage, camera2dImage);

        const peak::icv::PointCloudXYZRGB pointCloud(camera3dProjectedXyzImage, camera2dImage);

        const std::string outputFilePath = "textured_pointcloud.ply";

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
