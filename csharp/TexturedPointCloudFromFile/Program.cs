// Copyright (C) 2026, IDS Imaging Development Systems GmbH.
//
// Permission to use, copy, modify, and/or distribute this software for
// any purpose with or without fee is hereby granted.
//
// THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
// WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
// OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
// FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
// DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS.

using IDSImaging.Peak.Common.Types;
using IDSImaging.Peak.ICV;
using IDSImaging.Peak.ICV.Algorithms.Calibration;
using IDSImaging.Peak.ICV.Algorithms.Transformations;
using IDSImaging.Peak.ICV.Experimental.Algorithms.Transformations;
using IDSImaging.Peak.ICV.IO;
using IDSImaging.Peak.ICV.Types;

namespace TexturedPointCloudFromFile
{
    internal static class Program
    {
        private static int Main()
        {
            try
            {
                Library.Init();

                var dataPath = Path.Combine(AppContext.BaseDirectory);
                var camera3DPath = Path.Combine(dataPath, "3d_camera");
                var camera3DDepthMapPath = Path.Combine(camera3DPath, "depth_map.tiff");
                var camera3DCalibrationParametersPath = Path.Combine(camera3DPath, "calibration_parameters.json");

                var camera2DPath = Path.Combine(dataPath, "2d_camera");
                var camera2DImagePath = Path.Combine(camera2DPath, "color_image.png");
                var camera2DCalibrationParametersPath = Path.Combine(camera2DPath, "calibration_parameters.json");

                using var camera3DDepthMap = new Image(camera3DDepthMapPath, PixelFormat.Coord3D_C32f);
                using var camera2DImage = new Image(camera2DImagePath);

                var camera3DCalibrationParameters = new CalibrationParameters(camera3DCalibrationParametersPath);

                var camera2DCalibrationParameters = new CalibrationParameters(camera2DCalibrationParametersPath);

                using var undistortion = new Undistortion(camera3DCalibrationParameters.IntrinsicParameters);
                using UndistortedImage camera3DUndistortedDepthMap = undistortion.Process(camera3DDepthMap);

                using var camera3DXyzImage = new XYZImage(camera3DUndistortedDepthMap);

                var projection = new XYZProjection(
                    camera3DCalibrationParameters.ExtrinsicParameters,
                    camera2DCalibrationParameters);

                // Rearrange every point in the xyz image
                // to its corresponding 2d color pixel
                // to ensure 1:1 pixel index alignment
                // between depth and color data.
                using XYZImage camera3DProjectedXyzImage = projection.Process(camera3DXyzImage);

                using var pointCloud = new PointCloudXYZRGB(camera3DProjectedXyzImage, camera2DImage);

                const string outputFilePath = "textured_point_cloud.ply";

                var pointCloudWriter = new PointCloudWriter();
                pointCloudWriter.Write(outputFilePath, pointCloud);

                Console.WriteLine($"Point cloud saved to {outputFilePath}");
            }
            catch (Exception e)
            {
                Console.WriteLine("Error: " + e.Message);
                return -1;
            }
            finally
            {
                Library.Exit();
            }

            return 0;
        }
    }
}
