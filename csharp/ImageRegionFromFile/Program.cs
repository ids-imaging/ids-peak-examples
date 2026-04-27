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
using IDSImaging.Peak.Common.Types.Geometry;
using IDSImaging.Peak.ICV;
using IDSImaging.Peak.ICV.IO;
using IDSImaging.Peak.ICV.Types;
using IDSImaging.Peak.ICV.Algorithms.Thresholds;
using IDSImaging.Peak.ICV.Painting;

namespace IDSImaging.Peak.Examples.ImageRegionFromFile
{
    internal static class Program
    {
        private static int Main()
        {
            InitializeLibraries();

            try
            {
                var imageFilePath = Path.Combine(AppContext.BaseDirectory, "beads.png");

                Console.WriteLine($"Loading image {imageFilePath}.");
                using var inputImage = new Image(imageFilePath);

                var minuendRect = new Rectangle(
                    new Point(130, 80),
                    new Size(110, 150));

                var subtrahendRect = new Rectangle(
                    new Point(157, 117),
                    new Size(55, 75));

                // Compute region difference
                using Region region = new Region(minuendRect)
                    .Difference(new Region(subtrahendRect));

                Console.WriteLine("Set a region for the image.");
                inputImage.Region = region;

                Console.WriteLine("Applying a threshold on the reduced image region.");
                var threshold = new Threshold(new Interval(25, 255));
                using Region thresholdRegion = threshold.Process(inputImage);

                SaveResultToFile(inputImage, thresholdRegion, "image_reduced_region.png");

                Console.WriteLine("Reset image region to full image size.");
                inputImage.ResetRegion();

                using Region thresholdRegionFull = threshold.Process(inputImage);
                SaveResultToFile(inputImage, thresholdRegionFull, "image_full_region.png");
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

        // -------------------------------------------------------------------------------------------------------------
        // IMAGE OUTPUT
        // -------------------------------------------------------------------------------------------------------------

        private static void SaveResultToFile(
            Image inputImage,
            Region region,
            string imageFileName)
        {
            // For the painter an 8-bit color image is needed
            using Image rgbImage = inputImage.ConvertPixelFormat(PixelFormat.RGB8);

            var painter = new Painter(rgbImage);

            Console.WriteLine("Painting the used image region in green.");
            painter.Opacity = new Opacity(25);
            painter.Color = new Color(0, 255, 0);

            using Region imageRegion = inputImage.Region;
            painter.Draw(imageRegion);

            Console.WriteLine("Painting threshold result in red.");
            painter.Opacity = new Opacity(100);
            painter.Color = new Color(255, 0, 0);
            painter.Draw(region);

            var writer = new ImageWriter();

            var fullPath = Path.Combine(AppContext.BaseDirectory, imageFileName);
            writer.Write(fullPath, rgbImage);

            Console.WriteLine($"Saved image to {fullPath}.");
        }
    }
}
