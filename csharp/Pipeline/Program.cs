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

using System.IO;
using IDSImaging.Peak.Common.Types;
using IDSImaging.Peak.ICV;
using IDSImaging.Peak.ICV.IO;
using IDSImaging.Peak.ICV.Pipeline;
using IDSImaging.Peak.ICV.Pipeline.Types;
using IDSImaging.Peak.ICV.Types;

namespace IDSImaging.Peak.Samples.Pipeline
{
    /// <summary>
    /// This example demonstrates how to configure the image processing
    /// pipeline and how to process images loaded from disk.
    /// </summary>
    internal class Program
    {
        static void Main()
        {
            const string DATA_PATH = "../../data/pipeline_from_file/";

            // The library must be initialized before use.
            // Each call to `Init` must be matched with a corresponding call to `Exit`.
            Library.Init();

            try
            {
                // Create a new instance of the default pipeline used for processing
                using var pipeline = new DefaultPipeline();

                // Load raw camera image from disk
                using var image = new Image(Path.Combine(DATA_PATH, "input.bmp"), PixelFormat.BayerRG8);

                // Load the hotpixel reference image and perform detection.
                // This will automatically update the pipeline's hotpixel list.
                //
                // Recommended capture conditions when creating a reference image:
                // - Cover the camera sensor completely (no light should reach it).
                // - Set analog gain to maximum to amplify sensor noise.
                // - Set exposure time to maximum for better visibility of hotpixels.
                // - If necessary, reduce the frame rate to allow the maximum exposure.
                //
                // Following these steps ensures the detected hotpixels truly represent
                // persistent sensor defects rather than scene content or transient noise.
                using var hotpixelImage = new Image(Path.Combine(DATA_PATH, "hotpixel.bmp"), PixelFormat.BayerRG8);
                pipeline.Hotpixel.Detect(hotpixelImage, 1u, 13.8f);

                // Configure gain factors
                pipeline.Gain.Red = 1.92f;
                pipeline.Gain.Blue = 2.04f;

                // Configure color correction matrix
                pipeline.ColorCorrection.Matrix = new ColorCorrectionMatrix(new[]{
                    1.5039f, -0.4275f, -0.0625f,
                    -0.2539f, 1.4492f, -0.1914f,
                    0.1094f, -1.0625f, 1.9492f
                });

                // Configure gamma and digital black
                pipeline.Gamma.Value = 2.2f;
                pipeline.DigitalBlack.Value = 0.15f;

                // Configure the output pixel format
                pipeline.OutputPixelFormat = PixelFormat.RGB8;

                // Save the current pipeline configuration to disk.
                // The exported file can later be loaded with `ImportSettingsFromFile`,
                // restoring all settings exactly as configured at this point.
                pipeline.ExportSettingsToFile("pipelineSettings.json");

                // Process the loaded image
                using var result = pipeline.Process(image);

                // Write the resulting image to disk
                var imageWriter = new ImageWriter();
                imageWriter.Write("output.png", result);
            }
            finally
            {
                // One call to `Exit` is required for each call to `Init`.
                Library.Exit();
            }
        }
    }
}
