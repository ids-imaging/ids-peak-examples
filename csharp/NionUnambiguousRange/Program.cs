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
using IDSImaging.Peak.API;
using IDSImaging.Peak.API.Core;
using IDSImaging.Peak.API.Core.Nodes;
using IDSImaging.Peak.ICV.IO;
using IDSImaging.Peak.ICV.Types;

namespace IDSImaging.Peak.Examples.NionUnambiguousRange
{
    internal static class Program
    {
        private const float _startingPointMillimeter = 450.0f;
        private const int _imageAcquisitionCount = 1;

        private readonly struct UnambiguousRangeData
        {
            public UnambiguousRangeData(
                int startingPointDn,
                int scan3DAxisMax,
                float scaleFactor,
                float coordinateOffset,
                uint invalidDataValueDn)
            {
                StartingPointDn = startingPointDn;
                Scan3DAxisMax = scan3DAxisMax;
                ScaleFactor = scaleFactor;
                CoordinateOffset = coordinateOffset;
                InvalidDataValueDn = invalidDataValueDn;
            }

            public int StartingPointDn { get; }
            public int Scan3DAxisMax { get; }
            public float ScaleFactor { get; }
            public float CoordinateOffset { get; }
            public uint InvalidDataValueDn { get; }
        }

        private static int Main()
        {
            InitializeLibraries();

            try
            {
                using Device device = OpenFirstAvailableNionDevice();
                using NodeMap nodeMap = device.RemoteDevice().NodeMaps()[0];

                DeviceResetToDefault(nodeMap);

                float scaleFactor = (float) nodeMap.FindNode<FloatNode>("Scan3dCoordinateScale").Value();
                float coordinateOffset = (float) nodeMap.FindNode<FloatNode>("Scan3dCoordinateOffset").Value();
                int scan3DAxisMax = (int) nodeMap.FindNode<FloatNode>("Scan3dAxisMax").Value();
                uint invalidDataValueDn = (uint) nodeMap.FindNode<FloatNode>("Scan3dInvalidDataValue").Value();

                int startingPointDn = (int) Math.Round(
                    _startingPointMillimeter / scaleFactor,
                    MidpointRounding.AwayFromZero);
                int rangeMaximumDn = startingPointDn + scan3DAxisMax;

                Console.WriteLine($"Unambiguous range: [{startingPointDn}, {rangeMaximumDn}] [DN]");

                using DataStream dataStream = DeviceStartAcquisition(device, nodeMap);
                try
                {
                    for (int i = 0; i < _imageAcquisitionCount; i++)
                    {
                        using var guard = new BufferGuard(dataStream.WaitForFinishedBuffer(5000));
                        var buffer = guard.Buffer();

                        if (buffer.IsIncomplete())
                        {
                            Console.WriteLine($"Incomplete buffer {i}. Skipping.");
                            continue;
                        }

                        if (!buffer.HasNewData())
                        {
                            Console.WriteLine($"Buffer {i} has no new data. Skipping.");
                            continue;
                        }

                        using Image rawDepth = new Image(buffer.ToImageView());
                        var rangeData = new UnambiguousRangeData(
                            startingPointDn,
                            scan3DAxisMax,
                            scaleFactor,
                            coordinateOffset,
                            invalidDataValueDn);
                        Func<UnambiguousRangeData, Image> moveUnambiguousRange = data =>
                        {
                            Image mappedDepth = new Image(PixelFormat.Coord3D_C32f, rawDepth.Size);

                            unsafe
                            {
                                ushort* source = (ushort*) rawDepth.Data.ToPointer();
                                float* destination = (float*) mappedDepth.Data.ToPointer();

                                int rangeSpanDn = data.Scan3DAxisMax + 1;
                                int remainderOfAmbiguousRange = rangeSpanDn - data.StartingPointDn;
                                int pixelCount = checked((int) (rawDepth.SizeInBytes / sizeof(ushort)));

                                for (int pixelIndex = 0; pixelIndex < pixelCount; pixelIndex++)
                                {
                                    int value = source[pixelIndex];
                                    if ((uint) value == data.InvalidDataValueDn)
                                    {
                                        destination[pixelIndex] = data.InvalidDataValueDn;
                                        continue;
                                    }

                                    int shiftedDn = (value + remainderOfAmbiguousRange) % rangeSpanDn
                                        + data.StartingPointDn;
                                    destination[pixelIndex] =
                                        shiftedDn * data.ScaleFactor + data.CoordinateOffset;
                                }
                            }

                            return mappedDepth;
                        };
                        using Image depthMap = moveUnambiguousRange(rangeData);

                        WriteDepthMapToFile(depthMap, i);
                    }
                }
                finally
                {
                    DeviceStopAcquisition(nodeMap, dataStream);
                }
            }
            catch (Exception e)
            {
                Console.WriteLine($"Error: {e.Message}");
                return 1;
            }
            finally
            {
                ExitLibraries();
            }

            return 0;
        }

        private static void InitializeLibraries()
        {
            ICV.Library.Init();
            API.Library.Initialize();
        }

        private static void ExitLibraries()
        {
            try
            {
                ICV.Library.Exit();
                API.Library.Close();
            }
            catch (Exception e)
            {
                Console.WriteLine($"Error while closing IDS peak libraries: {e.Message}");
            }
        }

        private static Device OpenFirstAvailableNionDevice()
        {
            DeviceManager deviceManager = DeviceManager.Instance();
            deviceManager.Update();

            foreach (DeviceDescriptor descriptor in deviceManager.Devices())
            {
                if (descriptor.ModelName().IndexOf("nion", StringComparison.OrdinalIgnoreCase) < 0
                    || !descriptor.IsOpenable())
                {
                    continue;
                }

                return descriptor.OpenDevice(DeviceAccessType.Control);
            }

            throw new Exception("No IDS Nion device found.");
        }

        private static void DeviceResetToDefault(NodeMap nodeMap)
        {
            nodeMap.FindNode<EnumerationNode>("UserSetSelector").SetCurrentEntry("Default");

            using CommandNode command = nodeMap.FindNode<CommandNode>("UserSetLoad");
            command.Execute();
            command.WaitUntilDone();
        }

        private static DataStream DeviceStartAcquisition(Device device, NodeMap nodeMap)
        {
            nodeMap.FindNode<EnumerationNode>("ComponentSelector").SetCurrentEntry("Intensity");
            nodeMap.FindNode<BooleanNode>("ComponentEnable").SetValue(false);

            nodeMap.FindNode<EnumerationNode>("ComponentSelector").SetCurrentEntry("Confidence");
            nodeMap.FindNode<BooleanNode>("ComponentEnable").SetValue(false);

            DataStream dataStream = device.DataStreams()[0].OpenDataStream();
            nodeMap.FindNode<EnumerationNode>("AcquisitionMode").SetCurrentEntry("Continuous");

            uint payloadSize = (uint) nodeMap.FindNode<IntegerNode>("PayloadSize").Value();
            dataStream.AddAcquisitionBuffers(
                payloadSize,
                dataStream.NumBuffersAnnouncedMinRequired());

            nodeMap.FindNode<IntegerNode>("TLParamsLocked").SetValue(1);

            dataStream.StartAcquisition();
            nodeMap.FindNode<CommandNode>("AcquisitionStart").ExecuteAndWait();

            return dataStream;
        }

        private static void DeviceStopAcquisition(NodeMap nodeMap, DataStream dataStream)
        {
            nodeMap.FindNode<CommandNode>("AcquisitionStop").ExecuteAndWait();
            dataStream.StopAcquisition();
            nodeMap.FindNode<IntegerNode>("TLParamsLocked").SetValue(0);
            dataStream.FlushAndRevokeAllBuffers();
        }

        private static void WriteDepthMapToFile(Image depthMap, int i)
        {
            string path = $"depth_map_{i}.tiff";
            new ImageWriter().Write(path, depthMap);
            Console.WriteLine($"Depth map written to: {path}");
        }
    }
}
