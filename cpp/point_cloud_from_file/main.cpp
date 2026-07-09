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

        const peak::icv::Image depthMap(
            DATA_PATH "/point_cloud_from_file/depth_map.tiff", peak::common::PixelFormat::Coord3D_C32f);
        const peak::icv::CalibrationParameters calibrationParameters(
            DATA_PATH "/point_cloud_from_file/calibration_parameters.json");
        const peak::icv::Image intensityImage(DATA_PATH "/point_cloud_from_file/intensity.png");

        peak::icv::Undistortion undistortion(calibrationParameters.GetIntrinsicParameters());

        // Applies nearest-neighbor interpolation
        // during undistortion to strictly maintain measured physical geometry
        // and avoid calculating false, floating depth values.
        undistortion.SetInterpolation(peak::icv::Interpolation::NearestNeighbor);

        const peak::icv::UndistortedImage undistortedDepthMap = undistortion.Process(depthMap);
        const peak::icv::UndistortedImage undistortedIntensityImage = undistortion.Process(intensityImage);

        std::cout << "Create and save point cloud" << std::endl;
        const peak::icv::PointCloudXYZI pointCloud(undistortedDepthMap, undistortedIntensityImage);
        const peak::icv::PointCloudWriter writer;
        writer.Write("point_cloud.ply", pointCloud);

        peak::icv::library::Exit();
    }
    catch (const std::exception& e)
    {
        std::cout << e.what() << std::endl;
        return 1;
    }
    return 0;
}
