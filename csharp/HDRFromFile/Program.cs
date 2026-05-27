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

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using IDSImaging.Peak.ICV;
using IDSImaging.Peak.ICV.Types;
using IDSImaging.Peak.ICV.IO;
using IDSImaging.Peak.ICV.Experimental.Hdr;
using IDSImaging.Peak.ICV.Experimental.Hdr.ToneMapping;
using IDSImaging.Peak.Common.Types;

namespace IDSImaging.Peak.Examples.HdrFromFile
{
    /// <summary>
    /// This example demonstrates HDR image creation from multiple exposure images.
    /// It loads calibration and processing images from disk, estimates the camera response curve,
    /// generates an HDR image, and applies tone mapping to produce an LDR image.
    /// </summary>
    internal static class Program
    {

        // -------------------------------------------------------------------------------------------------------------
        // MAIN
        // -------------------------------------------------------------------------------------------------------------

        private static int Main()
        {
            InitializeLibraries();

            try
            {
                var writer = new ImageWriter();

                Console.WriteLine("Initialize HDR");
                using var hdr = new Hdr();

                Console.WriteLine($"Loading calibration images from {GetCalibrationImageFilePath()}");
                using DisposableList<Image> calibrationImages = ReadCalibrationImagesFromDir(GetCalibrationImageFilePath());

                // It is important to set the exposure time of the images to the images metadata
                SetImagesExposureMetaData(calibrationImages, GetExposureTimesCalibrationMicroSeconds());

                Console.WriteLine("Estimate camera response curve");
                hdr.EstimateResponseCurve(calibrationImages);

                Console.WriteLine($"Loading processing images from {GetProcessingImageFilePath()}");
                using DisposableList<Image> processingImages = ReadProcessingImagesFromDir(GetProcessingImageFilePath());

                // It is important to set the exposure time of the images to the images metadata
                SetImagesExposureMetaData(processingImages, GetExposureTimesProcessMicroSeconds());

                // It is also possible to skip the EstimateResponseCurve method, then response curve estimation is done on first call of Process method
                Console.WriteLine("Process HDR image");
                using Image hdrImage = hdr.Process(processingImages);

                writer.Write(GetHdrImageFilePath(), hdrImage);
                Console.WriteLine($"HDR image saved to {GetHdrImageFilePath()}");

                Console.WriteLine("Initialize tone mapping");
                using var toneMapping = new DragoToneMapping();

                Console.WriteLine("Tone mapping HDR image");
                using Image ldrImage = toneMapping.Process(hdrImage);

                writer.Write(GetToneMappedLdrImageFilePath(), ldrImage);
                Console.WriteLine($"Tone mapped image saved to {GetToneMappedLdrImageFilePath()}");
            }
            catch (Exception e)
            {
                Console.WriteLine("Error: " + e.Message);
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
                Console.WriteLine("Error while exiting libraries");
            }
        }

        // -------------------------------------------------------------------------------------------------------------
        // HDR UTILITIES
        // -------------------------------------------------------------------------------------------------------------

        private static List<double> GetExposureTimesCalibrationMicroSeconds()
        {
            return new List<double> { 502, 803, 1296, 2085, 3353, 5400, 8685, 13982, 22501 };
        }

        private static List<double> GetExposureTimesProcessMicroSeconds()
        {
            return new List<double> { 502, 1296, 3353, 8685, 22501 };
        }

        private static string GetCalibrationImageFilePath()
            => Path.Combine(AppContext.BaseDirectory, "calibration");

        private static string GetProcessingImageFilePath()
            => Path.Combine(AppContext.BaseDirectory, "processing");

        private static string GetHdrImageFilePath()
            => Path.Combine(AppContext.BaseDirectory, "hdr_image.tiff");

        private static string GetToneMappedLdrImageFilePath()
            => Path.Combine(AppContext.BaseDirectory, "tone_mapped_ldr_image.png");

        private static string ExposureToString(double exposure)
        {
            var s = exposure.ToString("F3", CultureInfo.InvariantCulture);
            return s.Replace('.', '_');
        }

        private static DisposableList<Image> ReadImagesFromDir(string directoryPath, List<double> exposureTimes)
        {
            var images = new DisposableList<Image>();

            foreach (var exposure in exposureTimes)
            {
                var filePath = Path.Combine(
                    directoryPath,
                    $"image_{ExposureToString(exposure / 1000.0)}_ms.png");

                images.Add(new Image(filePath));
            }

            return images;
        }

        private static void SetImagesExposureMetaData(DisposableList<Image> images, List<double> exposureTimes)
        {
            for (var i = 0; i < exposureTimes.Count; i++)
            {
                var meta = new Metadata();
                meta.SetValueByKey(MetadataKeys.DeviceExposureTime, exposureTimes[i]);
                images[i].Metadata = meta;
            }
        }

        private static DisposableList<Image> ReadCalibrationImagesFromDir(string path)
            => ReadImagesFromDir(path, GetExposureTimesCalibrationMicroSeconds());

        private static DisposableList<Image> ReadProcessingImagesFromDir(string path)
            => ReadImagesFromDir(path, GetExposureTimesProcessMicroSeconds());
    }
}
