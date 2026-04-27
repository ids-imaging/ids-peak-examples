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
using IDSImaging.Peak.Common.Types;
using IDSImaging.Peak.Common.Types.Geometry;
using IDSImaging.Peak.ICV;
using IDSImaging.Peak.ICV.IO;
using IDSImaging.Peak.ICV.Painting;
using IDSImaging.Peak.ICV.Types;

namespace IDSImaging.Peak.Examples.RegionMorphology
{
    internal static class Program
    {
        private static int Main()
        {
            InitializeLibraries();

            try
            {
                using Region region = CreateRegion();
                WriteRegionToImageFile(region, "region.png");

                var structuringElement = new Region(
                    new Rectangle(
                        new Point(-1, -1),
                        new Size(3, 3)));

                // Apply Dilation
                using Region regionDilated = region.Dilation(structuringElement);
                WriteRegionToImageFile(regionDilated, "region_dilated.png");

                // Apply Erosion
                using Region regionEroded = region.Erosion(structuringElement);
                WriteRegionToImageFile(regionEroded, "region_eroded.png");
            }
            catch (Exception e)
            {
                Console.WriteLine(e.Message);
                return 1;
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
        // REGION CREATION
        // -------------------------------------------------------------------------------------------------------------

        private static Region CreateRegion()
        {
            var region = new Region(new[]
            {
                new Point(2, 2),
                new Point(3, 2),
                new Point(4, 2),
                new Point(2, 3),
                new Point(3, 3),
                new Point(4, 3),
                new Point(2, 4),
                new Point(3, 4),
                new Point(4, 4),
                new Point(5, 4),
                new Point(3, 5)
            });

            return region;
        }

        // -------------------------------------------------------------------------------------------------------------
        // IMAGE CREATION
        // -------------------------------------------------------------------------------------------------------------

        private static unsafe Image CreateCheckerImage(Size size)
        {
            var image = new Image(PixelFormat.RGB8, size);

            byte* dataPtr = (byte*) image.Data.ToPointer();
            var width = image.Width;
            var height = image.Height;

            for (var r = 0; r < height; r++)
            {
                for (var c = 0; c < width; c++)
                {
                    var val = ((r + c) % 2 != 0) ? (byte) 50 : (byte) 205;

                    var pel = (r * width + c) * 3;
                    dataPtr[pel] = val;
                    dataPtr[pel + 1] = val;
                    dataPtr[pel + 2] = val;
                }
            }

            return image;
        }

        // -------------------------------------------------------------------------------------------------------------
        // OUTPUT
        // -------------------------------------------------------------------------------------------------------------

        private static void WriteRegionToImageFile(Region region, string outputFilename)
        {
            using Image rgbImage = CreateCheckerImage(new Size(8, 8));

            var painter = new Painter(rgbImage);
            painter.Draw(region);

            var writer = new ImageWriter();
            writer.Write(outputFilename, rgbImage);
        }
    }
}
