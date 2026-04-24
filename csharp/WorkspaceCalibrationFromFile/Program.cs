using System;
using System.IO;

using IDSImaging.Peak.Common.Types.Geometry;
using IDSImaging.Peak.ICV;
using IDSImaging.Peak.ICV.Algorithms.Calibration;
using IDSImaging.Peak.ICV.IO;
using IDSImaging.Peak.ICV.Types;
using IDSImaging.Peak.ICV.Types.Geometry;

namespace IDSImaging.Peak.Examples.WorkspaceCalibrationFromFile
{
    class Program
    {
        public static int Main()
        {
            InitializeLibraries();

            try
            {
                var baseDir = AppContext.BaseDirectory;

                // Load input calibration image.
                string inputImagePath = Path.Combine(baseDir, "workspace.png");
                Console.WriteLine("Loading image from " + inputImagePath);
                using var inputImage = new Image(inputImagePath);

                // Initialize calibration plate.
                Console.WriteLine("Initialize calibration");
                using var calibrationPlate = new CalibrationPlate(Path.Combine(baseDir, "1012041-radon-checkerboard-marker-65mm-6x6.json"));

                // Load intrinsic calibration parameters.
                string calibrationParametersPath = Path.Combine(baseDir, "intrinsic_parameters.json");
                Console.WriteLine("Loading calibration parameters from " + calibrationParametersPath);
                var calibrationParameters = new CalibrationParameters(calibrationParametersPath);
                var intrinsicParameters = calibrationParameters.IntrinsicParameters;

                // Create workspace calibration instance.
                var workspaceCalibration = new WorkspaceCalibration(intrinsicParameters, calibrationPlate);

                // Run workspace calibration.
                Console.WriteLine("Process workspace calibration");
                using var calibrationResult = workspaceCalibration.Process(inputImage);

                // Display the mean reprojection error.
                var meanReprojectionError = calibrationResult.MeanReprojectionError;
                Console.WriteLine("Calibration finished with mean reprojection error: " + meanReprojectionError);

                // Get the first view and print the convex hull points of the calibration plate.
                using var calibrationView = calibrationResult.Views[0];
                using PolygonF calibrationPlateConvexHull = calibrationView.ConvexHull;
                Console.WriteLine("Convex hull of the calibration plate:");
                foreach (PointF point in calibrationPlateConvexHull.Points)
                {
                    Console.WriteLine(point);
                }

                // Load an example point cloud.
                Console.WriteLine("Load example point cloud");
                using var pointCloud = new PointCloudXYZ(Path.Combine(baseDir, "point_cloud.ply"));

                // Transform the point cloud using the calibration view's extrinsic parameters.
                Console.WriteLine("Transform example point cloud");
                using var transformedPointCloud = pointCloud.TransformToWorkspace(calibrationView.ExtrinsicParameters);

                // Write out the transformed point cloud.
                Console.WriteLine("Write example point cloud");
                var writer = new PointCloudWriter();
                writer.Write("transformed_point_cloud.ply", transformedPointCloud);
            }
            catch (Exception e)
            {
                Console.WriteLine(e.Message);
                return -1;
            }
            finally
            {
                ExitLibraries();
            }

            return 0;
        }

        // -------------------------------------------------------------------------------------------------------------
        // PEAK LIBRARY LIFECYCLE
        // -------------------------------------------------------------------------------------------------------------

        private static void InitializeLibraries()
        {
            Library.Init();
        }

        private static void ExitLibraries()
        {
            try
            {
                Library.Exit();
            }
            catch (Exception)
            {
                Console.WriteLine("Error: Exception occurred while exiting library!");
            }
        }
    }
}
