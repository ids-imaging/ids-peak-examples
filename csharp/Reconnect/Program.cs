/// <summary>
/// The Reconnect example demonstrates how to detect device connection changes
/// and reliably handle temporary disconnections in a C# application using the
/// IDS peak API. It shows how to monitor device removal, loss of connection,
/// and subsequent reconnection, and how to safely resume image acquisition
/// once the device becomes available again.
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

using IDSImaging.Peak.API;
using IDSImaging.Peak.API.Core;
using IDSImaging.Peak.API.Core.Nodes;

namespace IDSImaging.Peak.Examples.Reconnect
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
                // Get the device manager singleton object.
                // WARNING: `using` the device manager instance would result
                //          in breaking the singleton
                var deviceManager = DeviceManager.Instance();
                bool acquisitionRunning = false;

                // IDSImaging.Peak.API provides several events that you can subscribe to in order
                // to be notified when the connection status of a device changes.
                //
                // The 'found' event is triggered if a new device is found upon calling
                // `DeviceManager.Update()`
                deviceManager.DeviceFoundEvent += (object sender, DeviceDescriptor foundDevice) =>
                {
                    Console.WriteLine($"Found-Device-Callback: Key={foundDevice.Key()}");
                };
                // The 'lost' event is only called for this application's opened devices if
                // a device is closed explicitly or if connection is lost while the reconnect is disabled,
                // otherwise the 'disconnected' event is triggered.
                // Other devices that were not opened or were opened by someone else still trigger
                // a 'lost' event.
                deviceManager.DeviceLostEvent += (object sender, string deviceKey) =>
                {
                    Console.WriteLine($"Lost-Device-Callback: Key={deviceKey}");
                };
                // Only called if the reconnect is enabled and if the device was previously opened by this
                // application instance.
                deviceManager.DeviceDisconnectedEvent += (object sender, DeviceDescriptor disconnectedDevice) =>
                {
                    Console.WriteLine($"Disconnected-Device-Callback: Key={disconnectedDevice.Key()}");
                };

                // When a device that was opened by the same application instance regains connection
                // after a previous disconnect the 'Reconnected' event is triggered.
                deviceManager.DeviceReconnectedEvent += (
                        object sender,
                        DeviceDescriptor reconnectedDevice,
                        DeviceReconnectInformation reconnectInformation) =>
                {
                    Console.WriteLine($"Reconnected-Device-Callback:\n" +
                            $"\tKey={reconnectedDevice.Key()}\n" +
                            $"\tReconnectSuccessful: {reconnectInformation.IsSuccessful()}\n" +
                            $"\tRemoteDeviceAcquisitionRunning: {reconnectInformation.IsRemoteDeviceAcquisitionRunning()}\n" +
                            $"\tRemoteDeviceConfigurationRestored: {reconnectInformation.IsRemoteDeviceConfigurationRestored()}\n");

                    // Using the `reconnectInformation` the user can tell whether they need to take actions
                    // in order to resume the image acquisition.
                    if (reconnectInformation.IsSuccessful())
                    {
                        // Device was reconnected successfully, nothing to do.
                        return;
                    }

                    EnsureCompatibleBuffersAndRestartAcquisition(reconnectedDevice, reconnectInformation);
                };
                deviceManager.DeviceListChangedEvent += (object sender) =>
                {
                    Console.WriteLine($"Device-List-Changed-Callback");
                };

                // Update the DeviceManager.
                // When `Update` is called, it searches for all producer libraries
                // contained in the directories found in the official GenICam GenTL
                // environment variable GENICAM_GENTL{32/64}_PATH. It then opens all
                // found ProducerLibraries, their Systems, their Interfaces, and lists
                // all available DeviceDescriptors.
                deviceManager.Update(DeviceManager.UpdatePolicy.ScanEnvironmentForProducerLibraries);

                Device device = null;
                foreach (var dev in deviceManager.Devices())
                {
                    if (dev.IsOpenable(DeviceAccessType.Control))
                    {
                        // Open the selected device with control access.
                        // The access types correspond to the GenTL `DEVICE_ACCESS_FLAGS`.
                        device = dev.OpenDevice(DeviceAccessType.Control);
                        break;
                    }
                }
                if (device == null)
                {
                    Console.WriteLine("No device found. Exiting program!");
                    return;
                }

                Console.WriteLine($"Using Device {device.DisplayName()}");

                // NOTE: `systemNodeMap` represents an unmanaged C++ resource.
                //       Use `using` (or call `Dispose` explicitly) to ensure deterministic
                //       cleanup when the object goes out of scope.
                using var systemNodeMap = device.ParentInterface().ParentSystem().NodeMaps()[0];
                if (!EnableReconnect(systemNodeMap))
                {
                    return;
                }

                // Retrieve the remote device's primary node map.
                // In GenICam, a node map represents a hierarchical set of parameters (features)
                // such as exposure, gain, and firmware info. The node map provides access to controls
                // implemented on the device itself, typically following the GenICam SFNC,
                // while allowing for device-specific extensions.
                using var remoteDeviceNodeMap = device.RemoteDevice().NodeMaps()[0];

                // NOTE: Uncommenting these lines will modify the PayloadSize without saving the
                // changes in the UserSet. If the device reboots (e.g. by losing and then regaining
                // power) the PayloadSize will have changed, which means the acquisition on
                // the remote device will not be restarted.
                // In order to restart the acquisition additional steps are required:
                // see "The payload size might have changed." above
                // remoteDeviceNodeMap.FindNode<IntegerNode>("Height").SetValue(512);
                // remoteDeviceNodeMap.FindNode<IntegerNode>("Width").SetValue(512);

                using var dataStream = device.DataStreams()[0].OpenDataStream();

                var payloadSize = (uint) remoteDeviceNodeMap.FindNode<IntegerNode>("PayloadSize").Value();
                var minBuffers = dataStream.NumBuffersAnnouncedMinRequired();
                for (int i = 0; i < minBuffers; i++)
                {
                    var buffer = dataStream.AllocAndAnnounceBuffer(payloadSize, IntPtr.Zero);
                    dataStream.QueueBuffer(buffer);
                }

                dataStream.StartAcquisition();
                remoteDeviceNodeMap.FindNode<CommandNode>("AcquisitionStart").Execute();
                acquisitionRunning = true;

                Console.CancelKeyPress += (sender, eventArgs) =>
                {
                    Console.WriteLine("KeyboardInterrupt: Exiting program...");
                    acquisitionRunning = false;
                    dataStream.KillWait();
                    // The process should not be terminated immediately.
                    eventArgs.Cancel = true;
                };

                Console.WriteLine("Now you can disconnect or reboot the device to trigger a reconnect!");
                while (acquisitionRunning)
                {
                    try
                    {
                        var buffer = dataStream.WaitForFinishedBuffer(IDSImaging.Peak.API.Core.Timeout.INFINITE_TIMEOUT);
                        Console.WriteLine($"Received Frame ID: {buffer.FrameID()}");
                        dataStream.QueueBuffer(buffer);
                    }
                    catch (Exception e)
                    {
                        Console.WriteLine($"Error getting frame: {e.Message}");
                    }
                }

                device?.Dispose();
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
        }

        static void EnsureCompatibleBuffersAndRestartAcquisition(DeviceDescriptor reconnectedDevice, DeviceReconnectInformation reconnectInformation)
        {
            using var device = reconnectedDevice.OpenedDevice();
            using var remoteDeviceNodeMap = device.RemoteDevice().NodeMaps()[0];
            using var dataStream = device.DataStreams()[0].OpenedDataStream();
            var payloadSize = (uint) remoteDeviceNodeMap.FindNode<IntegerNode>("PayloadSize").Value();

            bool hasPayloadSizeMismatch = payloadSize != dataStream.AnnouncedBuffers()[0].Size();

            // The payload size might have changed. In this case it's required to reallocate the buffers.
            if (hasPayloadSizeMismatch)
            {
                Console.WriteLine("PayloadSize has changed. Reallocating buffers...");

                bool isDataSteamGrabbing = dataStream.IsGrabbing();
                if (isDataSteamGrabbing)
                {
                    dataStream.StopAcquisition();
                }

                // Discard all buffers from the acquisition engine.
                // They remain in the announced buffer pool.
                dataStream.Flush(DataStreamFlushMode.DiscardAll);
                var numBuffersBefore = dataStream.AnnouncedBuffers().Count;

                // Remove them from the announced pool.
                foreach (var buffer in dataStream.AnnouncedBuffers())
                {
                    dataStream.RevokeBuffer(buffer);
                }

                // Allocate and queue the buffers using the new "PayloadSize".
                var minBuffers = dataStream.NumBuffersAnnouncedMinRequired();
                var numBuffers = Math.Max(minBuffers, numBuffersBefore);
                for (int i = 0; i < numBuffers; i++)
                {
                    var buffer = dataStream.AllocAndAnnounceBuffer(payloadSize, IntPtr.Zero);
                    dataStream.QueueBuffer(buffer);
                }

                if (isDataSteamGrabbing)
                {
                    dataStream.StartAcquisition();
                }
            }

            if (!reconnectInformation.IsRemoteDeviceAcquisitionRunning())
            {
                remoteDeviceNodeMap.FindNode<CommandNode>("AcquisitionStart").Execute();
            }

        }

        static bool EnableReconnect(NodeMap systemNodeMap)
        {
            if (!systemNodeMap.HasNode("ReconnectEnable"))
            {
                Console.WriteLine("ReconnectEnable not found!");
                return false;
            }

            var reconnectEnableNode = systemNodeMap.FindNode<BooleanNode>("ReconnectEnable");
            var reconnectEnableAccessStatus = reconnectEnableNode.AccessStatus();

            if (reconnectEnableAccessStatus == NodeAccessStatus.ReadWrite)
            {
                reconnectEnableNode.SetValue(true);
                return true;
            }

            if (reconnectEnableAccessStatus == NodeAccessStatus.ReadOnly)
            {
                if (reconnectEnableNode.Value())
                {
                    return true;
                }
            }

            Console.WriteLine("Error: ReconnectEnable cannot be set to true.");
            return false;
        }
    }
}
