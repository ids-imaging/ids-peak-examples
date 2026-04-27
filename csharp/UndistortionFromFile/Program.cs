// Copyright (C) 2026, IDS Imaging Development Systems GmbH.
//
// Permission to use, copy, modify, and/or distribute this software for
// any purpose with or without fee is hereby granted.
//
// THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
// WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
// OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
// FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
// DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
// AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
// OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

using System;
using System.IO;
using IDSImaging.Peak.ICV;
using IDSImaging.Peak.ICV.Algorithms.Calibration;
using IDSImaging.Peak.ICV.Algorithms.Transformations;
using IDSImaging.Peak.ICV.IO;
using IDSImaging.Peak.ICV.Types;

namespace IDSImaging.Peak.Examples.UndistortionFromFile
{
    internal static class Program
    {
        private static int Main()
        {
            InitializeLibraries();

            var baseDir = AppContext.BaseDirectory;

            var inputImagePath = Path.Combine(
                baseDir,
                "fisheye.png");

            var calibrationParametersPath = Path.Combine(baseDir, "calibration_parameters.json");

            try
            {
                Console.WriteLine($"Loading input image from {inputImagePath}");
                using var inputImage = new Image(inputImagePath);

                Console.WriteLine($"Loading intrinsic parameters from {calibrationParametersPath}");
                var calibrationParameters = new CalibrationParameters(calibrationParametersPath);

                Console.WriteLine("Initialize undistortion");
                using var undistortion = new Undistortion(
                    calibrationParameters.IntrinsicParameters);

                Console.WriteLine("Process undistortion");
                using UndistortedImage outputImage = undistortion.Process(inputImage);

                var writer = new ImageWriter();
                writer.Write("undistorted_image.png", outputImage);

                Console.WriteLine("Undistorted image saved");
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
