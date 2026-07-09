using System;
using System.IO;

using IDSImaging.Peak.Common.Types;
using IDSImaging.Peak.ICV;
using IDSImaging.Peak.ICV.Algorithms.Calibration;
using IDSImaging.Peak.ICV.Algorithms.Transformations;
using IDSImaging.Peak.ICV.IO;
using IDSImaging.Peak.ICV.Types;


namespace IDSImaging.Peak.Examples.PointCloudFromFile
{
    class Program
    {
        public static int Main()
        {
            InitializeLibraries();

            try
            {
                var baseDir = AppContext.BaseDirectory;

                Console.WriteLine("Read depth map from file");
                using var depthMap = new Image(Path.Combine(baseDir, "depth_map.tiff"), PixelFormat.Coord3D_C32f);

                Console.WriteLine("Read intensity image from file");
                using var intensityImage = new Image(Path.Combine(baseDir, "intensity.png"));

                Console.WriteLine("Read intrinsic parameters from file");
                var calibrationParameters = new CalibrationParameters(Path.Combine(baseDir, "calibration_parameters.json"));

                var writer = new PointCloudWriter();

                Console.WriteLine("Undistort depth map and intensity image");
                using var undistortion = new Undistortion(calibrationParameters.IntrinsicParameters);

                // Applies nearest-neighbor interpolation
                // during undistortion to strictly maintain measured physical geometry
                // and avoid calculating false, floating depth values.
                undistortion.Interpolation = Interpolation.NearestNeighbor;
                using var undistortedDepthMap = undistortion.Process(depthMap);
                using var undistortedIntensityImage = undistortion.Process(intensityImage);

                Console.WriteLine("Create and save point cloud");
                using var pointCloud = new PointCloudXYZI(undistortedDepthMap, undistortedIntensityImage);
                writer.Write("point_cloud.ply", pointCloud);
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
