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
using System.Collections.Generic;
using System.IO;
using IDSImaging.Peak.ICV;
using IDSImaging.Peak.ICV.Algorithms.Calibration;
using IDSImaging.Peak.ICV.IO;
using IDSImaging.Peak.ICV.Types;

namespace IDSImaging.Peak.Examples.CalibrationFromFile
{
    internal static class Program
    {
        private static int Main()
        {
            InitializeLibraries();

            try
            {
                var baseDir = AppContext.BaseDirectory;

                Console.WriteLine($"Loading images from {baseDir}");
                DisposableList<Image> inputImages = ReadImagesFromDir(baseDir);

                Console.WriteLine("Initialize calibration");

                var platePath = Path.Combine(
                    baseDir,
                    "1012041-radon-checkerboard-marker-65mm-6x6.json");

                using var calibrationPlate = new CalibrationPlate(platePath);
                var calibration = new CameraCalibration(calibrationPlate);

                Console.WriteLine("Process calibration");

                using CalibrationResult calibrationResult = calibration.Process(inputImages);

                var meanReprojectionError = calibrationResult.MeanReprojectionError;
                Console.WriteLine($"Calibration finished with mean reprojection error: {meanReprojectionError}");

                var outputFilePath = "calibration_result.json";
                var writer = new CalibrationResultWriter();
                writer.Write(outputFilePath, calibrationResult);

                Console.WriteLine($"Calibration result saved to file to {outputFilePath}");
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

        // Initialize peak ICV librarie
        private static void InitializeLibraries()
        {
            Library.Init();
        }

        // Shutdown peak libraries
        private static void ExitLibraries()
        {
            try
            {
                Library.Exit();
            }
            catch (Exception)
            {
                Console.WriteLine("Error: Exception occured while exiting library!");
            }
        }

        // -------------------------------------------------------------------------------------------------------------
        // FILE INPUT
        // -------------------------------------------------------------------------------------------------------------

        private static DisposableList<Image> ReadImagesFromDir(string directoryPath)
        {
            const int numImages = 16;
            var images = new DisposableList<Image>();

            for (var i = 0; i < numImages; i++)
            {
                var filename = Path.Combine(
                    directoryPath,
                    $"image_{(i + 1):D2}.png");

                images.Add(new Image(filename));
            }

            return images;
        }
    }
}
