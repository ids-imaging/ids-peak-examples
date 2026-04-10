/*
 * Copyright(C) 2026, IDS Imaging Development Systems GmbH.
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

        constexpr auto workspaceImagePath = DATA_PATH "/workspace_calibration_from_file/workspace.png";
        std::cout << "Loading workspace image from " << workspaceImagePath << std::endl;
        const auto inputImage = peak::icv::Image{ workspaceImagePath };

        std::cout << "Initialize calibration" << std::endl;
        const peak::icv::CalibrationPlate calibrationPlate(
            DATA_PATH "/workspace_calibration_from_file/1012041-radon-checkerboard-marker-65mm-6x6.json");

        constexpr auto calibrationParametersPath = DATA_PATH
            "/workspace_calibration_from_file/intrinsic_parameters.json";
        std::cout << "Loading calibration parameters from " << calibrationParametersPath << std::endl;
        const peak::icv::CalibrationParameters calibrationParameters(calibrationParametersPath);

        const peak::icv::WorkspaceCalibration workspaceCalibration(
            calibrationParameters.GetIntrinsicParameters(), calibrationPlate);

        std::cout << "Process workspace calibration" << std::endl;
        const auto calibrationResult = workspaceCalibration.Process(inputImage);

        const auto meanReprojectionError = calibrationResult.GetMeanReprojectionError();
        std::cout << "Calibration finished with mean reprojection error: " << meanReprojectionError << std::endl;

        const auto calibrationView = calibrationResult.GetViews().at(0);
        const auto calibrationPlateConvexHull = calibrationView.GetConvexHull();

        std::cout << "Convex hull of the calibration plate:" << std::endl;
        for (const auto& point : calibrationPlateConvexHull.GetPoints())
        {
            std::cout << point << std::endl;
        }

        std::cout << "Load example point cloud" << std::endl;
        peak::icv::PointCloudXYZ pointCloud(DATA_PATH "/workspace_calibration_from_file/point_cloud.ply");

        std::cout << "Transform example point cloud" << std::endl;
        const auto transformedPointCloud = pointCloud.TransformToWorkspace(calibrationView.GetExtrinsicParameters());

        std::cout << "Write example point cloud" << std::endl;
        peak::icv::PointCloudWriter writer;
        writer.Write("transformed_point_cloud.ply", transformedPointCloud);

        peak::icv::library::Exit();
    }
    catch (const std::exception& e)
    {
        std::cout << e.what() << std::endl;
        return 1;
    }
    return 0;
}
