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
using IDSImaging.Peak.ICV.Algorithms.Calibration;
using IDSImaging.Peak.ICV.Algorithms.Thresholds;
using IDSImaging.Peak.ICV.Algorithms.Transformations;
using IDSImaging.Peak.ICV.IO;
using IDSImaging.Peak.ICV.Types;
using IDSImaging.Peak.API;
using IDSImaging.Peak.API.Core;
using IDSImaging.Peak.API.Core.File;
using IDSImaging.Peak.API.Core.Nodes;
using Buffer = IDSImaging.Peak.API.Core.Buffer;


namespace IDSImaging.Peak.Examples.NionPointCloud
{
    /// <summary>
    /// This example shows how to open and configure an IDS Nion camera.
    /// It demonstrates how to acquire multipart image buffers containing a depth map and an intensity image,
    /// and process this data into usable 3D information using the IDS peak ICV and generic APIs.
    /// </summary>
    /// <remarks>
    /// <para>
    /// The application:
    /// <list type="bullet">
    /// <item><description>Opens the first connected IDS Nion camera</description></item>
    /// <item><description>Configures camera parameters such as exposure time and confidence threshold</description></item>
    /// <item><description>Acquires multipart image data (depth map and intensity image)</description></item>
    /// <item><description>Converts the raw depth map into metric floating-point coordinates</description></item>
    /// <item><description>Filters invalid and out-of-range depth values</description></item>
    /// <item><description>Undistorts depth and intensity images using factory calibration data</description></item>
    /// <item><description>Generates a 3D point cloud with per-point intensity values (XYZI)</description></item>
    /// <item><description>Writes depth maps, intensity images, and point cloud files to disk</description></item>
    /// </list>
    /// </para>
    /// </remarks>
    internal static class Program
    {
        // -------------------------------------------------------------------------------------------------------------
        // CONFIGURATION
        // -------------------------------------------------------------------------------------------------------------

        // Enable filtering of depth values based on the camera confidence image
        private const bool _filterDepthMapByConfidenceEnabled = true;

        // Pixels with confidence values below this threshold are marked as invalid. The Range is 0 to 4095.
        private const int _confidenceThreshold = 100;

        // Camera exposure time in microseconds
        private const float _exposureTimeUs = 1000.0f;

        // Enable filtering of depth values based on the Z distance
        private const bool _filterDistanceEnabled = true;

        // Valid Z distance interval in millimeters
        private static readonly IntervalF _filterDistanceIntervalMm = new IntervalF(100.0f, 1000.0f);

        // Number of images acquired in this example
        private const int _imageAcquisitionCount = 10;


        // -------------------------------------------------------------------------------------------------------------
        // MAIN
        // -------------------------------------------------------------------------------------------------------------

        private static int Main()
        {
            InitializeLibraries();

            try
            {
                using Device device = OpenFirstConnectedDevice();
                using NodeMap nodeMap = device.RemoteDevice().NodeMaps()[0];

                DeviceResetToDefault(nodeMap);

                if (_filterDepthMapByConfidenceEnabled)
                {
                    DeviceSetConfidenceThreshold(nodeMap, _confidenceThreshold);
                }

                DeviceSetExposureTime(nodeMap);

                CalibrationParameters calibration = DeviceReadCalibrationParameters(nodeMap);
                var min = DeviceGetDepthMinimumValidValue(nodeMap);
                var max = DeviceGetDepthMaximumValidValue(nodeMap);
                var scale = DeviceGetDepthScaleFactor(nodeMap);

                // Undistortion object initialized with factory calibration data
                using var undistortion = new Undistortion(calibration);

                // Applies nearest-neighbor interpolation
                // during undistortion to strictly maintain measured physical geometry
                // and avoid calculating false, floating depth values.
                undistortion.Interpolation = Interpolation.NearestNeighbor;

                using DataStream stream = DeviceStartAcquisition(device, nodeMap);

                for (var i = 0; i < _imageAcquisitionCount; i++)
                {
                    using Buffer buffer = stream.WaitForFinishedBuffer(DataStream.INFINITE_NUMBER);

                    if (buffer.IsIncomplete())
                    {
                        Console.WriteLine($"Incomplete buffer {i}. Skipping.");
                        stream.QueueBuffer(buffer);
                        continue;
                    }

                    if (!buffer.HasNewData())
                    {
                        Console.WriteLine($"Buffer {i} has no new data. Skipping.");
                        stream.QueueBuffer(buffer);
                        continue;
                    }

                    if (!buffer.HasParts())
                    {
                        throw new Exception("Buffer has no parts. Aborting.");
                    }

                    (BufferPart depthPart, BufferPart intensityPart) = ExtractBufferParts(buffer);

                    // -------------------------------------------------------------------------------------------------
                    // Depth map processing
                    // -------------------------------------------------------------------------------------------------

                    // Create image from raw depth buffer and attach metadata
                    using var rawDepth = new Image(depthPart.ToImageView());
                    rawDepth.Metadata = AppendMetadataByDeviceMetadata(rawDepth.Metadata, nodeMap);

                    // Convert depth values to floating-point metric coordinates
                    using Image depth = rawDepth.ConvertPixelFormatWithFactor(
                        PixelFormat.Coord3D_C32f, scale);

                    // Remove invalid depth pixels and get region of only valid pixels
                    var validPixelThreshold = new ThresholdF(new IntervalF(min, max));
                    using Region region = validPixelThreshold.Process(depth);
                    depth.Region = region;

                    // Undistort the depth map
                    using UndistortedImage undistortedDepth = undistortion.Process(depth);

                    // Optional distance-based filtering
                    if (_filterDistanceEnabled)
                    {
                        var distanceFilter = new ThresholdF(_filterDistanceIntervalMm);
                        undistortedDepth.Region = distanceFilter.Process(undistortedDepth);
                    }

                    WriteDepthMapToFile(undistortedDepth, i);

                    // -------------------------------------------------------------------------------------------------
                    // Intensity image processing
                    // -------------------------------------------------------------------------------------------------
                    using var intensity = new Image(intensityPart.ToImageView());
                    intensity.Metadata = AppendMetadataByDeviceMetadata(intensity.Metadata, nodeMap);

                    using UndistortedImage undistortedIntensity = undistortion.Process(intensity);
                    WriteIntensityToFile(undistortedIntensity, i);

                    // Queue buffer that it can be reused. This can be done after the buffer data is no longer used.
                    stream.QueueBuffer(buffer);

                    // -------------------------------------------------------------------------------------------------
                    // Point cloud generation
                    // -------------------------------------------------------------------------------------------------

                    using var pointCloud = new PointCloudXYZI(undistortedDepth, undistortedIntensity);

                    // Applies the extrinsic calibration parameters from the factory calibration
                    // to shift the coordinate system's origin
                    // from the optical center directly to the front housing of the Nion camera.
                    // Alternatively, a workspace calibration can be performed
                    // to define the origin at any desired location within the scene.
                    using var transformedPointCloud = pointCloud.TransformToWorkspace(calibration.ExtrinsicParameters);

                    WritePointCloudToFile(transformedPointCloud, i);
                }

                DeviceStopAcquisition(nodeMap, stream);
            }
            catch (Exception e)
            {
                Console.WriteLine("Error: " + e.Message);
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

        // Initialize peak core and peak ICV libraries
        private static void InitializeLibraries()
        {
            ICV.Library.Init();
            API.Library.Initialize();
        }

        // Shutdown peak libraries
        private static void ExitLibraries()
        {
            try
            {
                ICV.Library.Exit();
                API.Library.Close();
            }
            catch (Exception)
            {
                Console.WriteLine("Error: Exception occured while exiting libraries!");
            }
        }

        // -------------------------------------------------------------------------------------------------------------
        // DEVICE UTILITIES
        // -------------------------------------------------------------------------------------------------------------

        private static Device OpenFirstConnectedDevice()
        {
            using var deviceManager = DeviceManager.Instance();
            deviceManager.Update();

            foreach (DeviceDescriptor deviceDescriptor in deviceManager.Devices())
            {
                if (!deviceDescriptor.ModelName().Contains("NION") || !deviceDescriptor.IsOpenable())
                {
                    continue;
                }

                Device device = deviceDescriptor.OpenDevice(DeviceAccessType.Control);

                return device;
            }

            throw new Exception("No IDS Nion device found.");
        }

        private static void DeviceResetToDefault(NodeMap nodeMap)
        {
            nodeMap.FindNode<EnumerationNode>("UserSetSelector").SetCurrentEntry("Default");

            using CommandNode cmd = nodeMap.FindNode<CommandNode>("UserSetLoad");
            cmd.Execute();
            cmd.WaitUntilDone();
        }

        private static void DeviceSetConfidenceThreshold(NodeMap nodeMap, int threshold)
        {
            // Sets the gray value of all pixels in the Range component whose corresponding value in the Confidence
            // component is below the set threshold to Scan3dInvalidDataValue.
            nodeMap.FindNode<IntegerNode>("Scan3dRangeConfidenceThreshold").SetValue(threshold);
        }

        private static void DeviceSetExposureTime(NodeMap nodeMap)
        {
            nodeMap.FindNode<FloatNode>("ExposureTime").SetValue(_exposureTimeUs);
        }

        private static CalibrationParameters DeviceReadCalibrationParameters(NodeMap nodeMap)
        {
            using var adapter = new FileAdapter(nodeMap, "LensCalibrationData");

            if (adapter.Size() <= 0)
            {
                throw new Exception("No factory calibration data available.");
            }

            return new CalibrationParameters(adapter.Read(adapter.Size()));
        }

        private static float DeviceGetDepthMinimumValidValue(NodeMap nodeMap)
            => (float) nodeMap.FindNode<FloatNode>("Scan3dAxisMin").Value();

        private static float DeviceGetDepthMaximumValidValue(NodeMap nodeMap)
            => (float) nodeMap.FindNode<FloatNode>("Scan3dAxisMax").Value();

        // Get the scale factor for converting depth values into metric units
        private static float DeviceGetDepthScaleFactor(NodeMap nodeMap)
            => (float) nodeMap.FindNode<FloatNode>("Scan3dCoordinateScale").Value();

        // Append a metadata object with device binning and ROI information
        // The metadata is required for correct undistortion of images.
        private static Metadata AppendMetadataByDeviceMetadata(Metadata metadata, NodeMap nodeMap)
        {
            metadata.SetValueByKey(MetadataKeys.BinningHorizontal,
                (uint) nodeMap.FindNode<IntegerNode>("BinningHorizontal").Value());

            metadata.SetValueByKey(MetadataKeys.BinningVertical,
                (uint) nodeMap.FindNode<IntegerNode>("BinningVertical").Value());

            var roi = new RectangleU(
                (uint) nodeMap.FindNode<IntegerNode>("OffsetX").Value(),
                (uint) nodeMap.FindNode<IntegerNode>("OffsetY").Value(),
                (uint) nodeMap.FindNode<IntegerNode>("Width").Value(),
                (uint) nodeMap.FindNode<IntegerNode>("Height").Value());

            metadata.SetValueByKey(MetadataKeys.Roi, roi);

            return metadata;
        }

        // -------------------------------------------------------------------------------------------------------------
        // ACQUISITION
        // -------------------------------------------------------------------------------------------------------------

        private static DataStream DeviceStartAcquisition(Device device, NodeMap nodeMap)
        {
            DataStream stream = device.DataStreams()[0].OpenDataStream();

            nodeMap.FindNode<EnumerationNode>("AcquisitionMode").SetCurrentEntry("Continuous");

            var payloadSize = (uint) nodeMap.FindNode<IntegerNode>("PayloadSize").Value();

            for (var i = 0; i < stream.NumBuffersAnnouncedMinRequired(); i++)
            {
                stream.QueueBuffer(stream.AllocAndAnnounceBuffer(payloadSize, IntPtr.Zero));
            }

            nodeMap.FindNode<IntegerNode>("TLParamsLocked").SetValue(1);

            stream.StartAcquisition();

            using CommandNode cmd = nodeMap.FindNode<CommandNode>("AcquisitionStart");
            cmd.Execute();
            cmd.WaitUntilDone();

            return stream;
        }

        private static (BufferPart depth, BufferPart intensity) ExtractBufferParts(Buffer buffer)
        {
            BufferPart depth = null;
            BufferPart intensity = null;

            foreach (BufferPart part in buffer.Parts())
            {
                if (part.Type() == BufferPartType.Image3D)
                {
                    depth = part;
                }
                else if (part.Type() == BufferPartType.Image2D)
                {
                    intensity = part;
                }
            }

            if (depth == null || intensity == null)
            {
                throw new Exception("Missing buffer parts");
            }

            return (depth, intensity);
        }

        private static void DeviceStopAcquisition(NodeMap nodeMap, DataStream stream)
        {
            using CommandNode cmd = nodeMap.FindNode<CommandNode>("AcquisitionStop");
            cmd.Execute();
            cmd.WaitUntilDone();

            stream.StopAcquisition();
            nodeMap.FindNode<IntegerNode>("TLParamsLocked").SetValue(0);

            stream.Flush(DataStreamFlushMode.DiscardAll);

            foreach (Buffer b in stream.AnnouncedBuffers())
            {
                stream.RevokeBuffer(b);
            }
        }

        // -------------------------------------------------------------------------------------------------------------
        // FILE OUTPUT
        // -------------------------------------------------------------------------------------------------------------
        private static void WriteDepthMapToFile(Image depthMap, int i)
        {
            var writer = new ImageWriter();
            var path = $"undistorted_depth_map_{i}.tiff";
            writer.Write(path, depthMap);
            Console.WriteLine(path);
        }

        private static void WriteIntensityToFile(Image intensity, int i)
        {
            var writer = new ImageWriter();
            var path = $"undistorted_intensity_image_{i}.png";
            writer.Write(path, intensity);
            Console.WriteLine(path);
        }

        private static void WritePointCloudToFile(PointCloudXYZI pointCloud, int i)
        {
            var writer = new PointCloudWriter();
            var path = $"point_cloud_xyzi_{i}.ply";
            writer.Write(path, pointCloud);
            Console.WriteLine(path);
        }
    }
}
