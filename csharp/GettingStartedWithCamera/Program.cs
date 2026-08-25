/// <summary>
/// This application demonstrates how to open the first available camera
/// to acquire images.
/// </summary>
/// <license>
/// Copyright (C) 2026, IDS Imaging Development Systems GmbH.
///
/// Permission to use, copy, modify, and/or distribute this software for
/// any purpose with or without fee is hereby granted.
///
/// THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
/// WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
/// OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
/// FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
/// DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
/// AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
/// OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
/// </license>
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using IDSImaging.Peak.API;
using IDSImaging.Peak.API.Core;
using IDSImaging.Peak.API.Core.Nodes;
using IDSImaging.Peak.ICV.Types;

namespace IDSImaging.Peak.Examples.GettingStartedWithCamera
{
    internal class Program
    {
        static void Main(string[] args)
        {
            try
            {
                // Initialize libraries
                ICV.Library.Init();
                API.Library.Initialize();

                // Initialize DeviceManager and update device list
                var deviceManager = DeviceManager.Instance();
                deviceManager.Update();

                // Find the first available camera with control access
                var deviceDescriptor = deviceManager.FirstAvailableDevice(DeviceAccessType.Control);

                if (deviceDescriptor == null)
                {
                    Console.WriteLine("Failed to find any openable camera!");
                    ICV.Library.Exit();
                    API.Library.Close();
                    Console.ReadKey();
                    return;
                }

                // Open the device and get the nodemap of the remote device
                using var device = deviceDescriptor.OpenDevice(DeviceAccessType.Control);
                using var nodeMapRemoteDevice = device.RemoteDevice().NodeMaps()[0];

                // Open the data stream and prepare the buffers
                using var dataStream = device.DataStreams()[0].OpenDataStream();

                // Get the required payload size. If the data stream does not
                // define it, fall back to the remote device node map.
                var payloadSizeNode = nodeMapRemoteDevice.FindNode<IntegerNode>("PayloadSize");
                var payloadSize = dataStream.DefinesPayloadSize() ? dataStream.PayloadSize() :
                                                                      (uint) payloadSizeNode.Value();

                var bufferCount = dataStream.NumBuffersAnnouncedMinRequired();

                // Allocate buffers and queue them
                dataStream.AddAcquisitionBuffers(payloadSize, bufferCount);

                // Lock transport layer parameters (TLParamsLocked = 1) to
                // prevent irregular access to the remote device during acquisition
                nodeMapRemoteDevice.FindNode<IntegerNode>("TLParamsLocked").SetValue(1);

                // Start acquisition on both data stream and device
                dataStream.StartAcquisition();
                nodeMapRemoteDevice.FindNode<CommandNode>("AcquisitionStart").ExecuteAndWait();

                Console.WriteLine("Acquisition started. Capturing 5 ICV images...");

                // Acquire 5 images and wrap them as ICV images
                for (int i = 0; i < 5; ++i)
                {
                    // Wait for a filled buffer (timeout: 5000 ms)
                    using var guard = new BufferGuard(dataStream.WaitForFinishedBuffer(5000));

                    // Create an ICV image from the buffer
                    using var image = new Image(guard.Buffer().ToImageView());

                    // The image can now be used for further processing
                    Console.WriteLine(
                        $"Image {i + 1} captured! " +
                        $"ICV dimensions: {image.Size} px, " +
                        $"PixelFormat: {image.PixelFormat}");
                }

                // Stop acquisition
                nodeMapRemoteDevice.FindNode<CommandNode>("AcquisitionStop").ExecuteAndWait();
                dataStream.StopAcquisition(AcquisitionStopMode.Default);

                // Unlock transport layer parameters
                nodeMapRemoteDevice.FindNode<IntegerNode>("TLParamsLocked").SetValue(0);

                // Release acquisition buffers
                dataStream.FlushAndRevokeAllBuffers();

                Console.WriteLine("Camera closed and resources released successfully.");
            }
            catch (Exception e)
            {
                Console.WriteLine($"Error: {e.Message}");
            }

            try
            {
                // Close libraries
                ICV.Library.Exit();
                API.Library.Close();
            }
            catch (Exception e)
            {
                Console.WriteLine($"Error: {e.Message}");
            }

            Console.WriteLine("\nPress any key to exit...");
            Console.ReadKey();
        }
    }
}
