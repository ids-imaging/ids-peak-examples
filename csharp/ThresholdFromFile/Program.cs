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
using IDSImaging.Peak.Common.Types;
using IDSImaging.Peak.ICV;
using IDSImaging.Peak.ICV.Algorithms.Thresholds;
using IDSImaging.Peak.ICV.IO;
using IDSImaging.Peak.ICV.Painting;
using IDSImaging.Peak.ICV.Types;

namespace IDSImaging.Peak.Examples.ThresholdFromFile
{
    internal static class Program
    {
        private static int Main()
        {
            InitializeLibraries();

            try
            {
                var baseDir = AppContext.BaseDirectory;

                var inputImageFilePath = Path.Combine(
                    baseDir,
                    "beads.png");

                Console.WriteLine($"Loading image {inputImageFilePath}");
                using var inputImage = new Image(inputImageFilePath);

                // For thresholding a grayscale image is needed
                Interval intervalRange = Threshold.GetRange(inputImage);

                var thresholdInterval = new Interval(25, 255);

                Console.WriteLine(
                    $"Setting the interval [{thresholdInterval.Minimum}, {thresholdInterval.Maximum}] " +
                    $"for the threshold within the range of [{intervalRange.Minimum}, {intervalRange.Maximum}]");

                var threshold = new Threshold(thresholdInterval);

                using Region region = threshold.Process(inputImage);

                // For the painter, an 8-bit color image is needed
                using Image rgbImage = inputImage.ConvertPixelFormat(PixelFormat.RGB8);

                var painter = new Painter(rgbImage);
                painter.Draw(region);

                var writer = new ImageWriter();
                var outputFilePath = Path.Combine(
                    baseDir,
                    "image_thresholded.png");

                writer.Write(outputFilePath, rgbImage);
                Console.WriteLine($"Saved image to {outputFilePath}");
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
