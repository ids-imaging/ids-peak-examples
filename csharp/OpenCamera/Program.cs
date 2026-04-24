/// <summary>
/// This example demonstrates how to use the IDS peak DeviceManager to discover,
/// select, and open a camera. After opening the device with control access,
/// basic device information is retrieved from the remote GenICam node map.
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

namespace IDSImaging.Peak.Examples.OpenCamera
{
    internal class Program
    {
        static void Main(string[] args)
        {
            // The library must be initialized before use.
            // Each call to `Initialize` must be matched with a corresponding call to `Close`.
            Library.Initialize();

            try
            {
                Console.WriteLine("IDS peak OpenCamera Example");

                // Get the device manager singleton object.
                // WARNING: `using` the device manager instance would result
                //          in breaking the singleton
                var deviceManager = DeviceManager.Instance();

                // Update the device manager. When `Update` is called, it
                // searches for all ProducerLibraries found in the directories
                // specified by the GENICAM_GENTL{32/64}_PATH environment
                // variable. It then opens all producers, their systems and
                // interfaces, and lists all available DeviceDescriptors.
                deviceManager.Update();

                // Exit program if no device was found.
                if (!deviceManager.Devices().Any())
                {
                    Console.WriteLine("No device found. Exiting program.");
                    Console.ReadKey();
                    return;
                }

                // List all available devices.
                uint i = 0;
                var devices = deviceManager.Devices();

                Console.WriteLine("Devices available: ");

                foreach (var deviceDescriptor in devices)
                {
                    Console.WriteLine(
                        $"{i}: {deviceDescriptor.ModelName()} "
                            + $"({deviceDescriptor.ParentInterface().DisplayName()}; "
                            + $"{deviceDescriptor.ParentInterface().ParentSystem().DisplayName()} "
                            + $"v.{deviceDescriptor.ParentInterface().ParentSystem().Version()})"
                    );
                    ++i;
                }

                // Select a device to open.
                int selectedDevice = 0;
                // Prompt user for device index or remove this block to always use the first device.
                Console.WriteLine("\nSelect device to open: ");
                if (!int.TryParse(Console.ReadLine(), out selectedDevice))
                {
                    Console.WriteLine("Invalid input — using device 0.");
                    selectedDevice = 0;
                }

                // Open the selected device with control access.
                // The access types correspond to the GenTL `DEVICE_ACCESS_FLAGS`.
                // NOTE: `device` represents an unmanaged C++ resource.
                //       Use `using` (or call `Dispose` explicitly) to ensure deterministic
                //       cleanup when the object goes out of scope.
                using var device = devices[selectedDevice].OpenDevice(DeviceAccessType.Control);

                // Retrieve the remote device's primary node map.
                // In GenICam, a node map represents a hierarchical set of parameters (features)
                // such as exposure, gain, and firmware info. The node map provides access to controls
                // implemented on the device itself, typically following the GenICam SFNC, while allowing for
                // device-specific extensions.
                using var nodeMapRemoteDevice = device.RemoteDevice().NodeMaps()[0];

                // Print model name using the "DeviceModelName" node.
                Console.WriteLine(
                    $"Model Name: {TryReadString(nodeMapRemoteDevice, "DeviceModelName")}"
                );

                // Print user ID using the "DeviceUserID" node.
                Console.WriteLine($"User ID: {TryReadString(nodeMapRemoteDevice, "DeviceUserID")}");

                // Print sensor information using the "SensorName" node.
                Console.WriteLine(
                    $"Sensor Name: {TryReadString(nodeMapRemoteDevice, "SensorName")}"
                );

                try
                {
                    // Print maximum sensor resolution (width x height).
                    var widthMax = nodeMapRemoteDevice.FindNode<IntegerNode>("WidthMax").Value();

                    var heightMax = nodeMapRemoteDevice.FindNode<IntegerNode>("HeightMax").Value();

                    Console.WriteLine($"Max. resolution (w x h): {widthMax} x {heightMax}");
                }
                catch (Exception)
                {
                    // If "WidthMax"/"HeightMax" are not valid or implemented nodes.
                    Console.WriteLine("Max. resolution (w x h): (unknown)");
                }
            }
            catch (Exception e)
            {
                Console.WriteLine($"EXCEPTION: {e.Message}");
            }
            finally
            {
                // One call to `Close` is required for each call to `Initialize`.
                Library.Close();
            }

            Console.WriteLine("\nPress any key to exit...");
            Console.ReadKey();
        }

        static string TryReadString(NodeMap nodeMap, string nodeName)
        {
            try
            {
                return nodeMap.FindNode<StringNode>(nodeName).Value();
            }
            catch
            {
                return "(unknown)";
            }
        }
    }
}
