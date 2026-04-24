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
using System.Collections.Generic;

using IDSImaging.Peak.API;
using IDSImaging.Peak.API.Core;
using IDSImaging.Peak.API.Core.Nodes;

namespace IDSImaging.Peak.Examples.SystemTimestamp
{
    /// <summary>
    /// This example demonstrates how to use the IDS peak DeviceManager to discover,
    /// select, and open a camera that supports system timestamp synchronization.
    /// The device is configured for freerun acquisition, image buffers are acquired,
    /// and buffer system timestamps (nanoseconds since Unix epoch) are retrieved
    /// and converted into structured local and UTC time representations.
    ///
    /// In addition, if supported by the device, remote ExposureStart events are
    /// enabled. The example shows how to correlate remote device timestamps with
    /// the host system timestamp domain using the synchronization latch mechanism,
    /// allowing event timestamps to be translated into system time.
    /// </summary>
    internal static class Program
    {
        private const int IMAGE_COUNT_MAX = 10;

        private static void Main(string[] args)
        {
            // The library must be initialized before use.
            // Each call to `Initialize` must be matched with a corresponding call to `Close`.
            Library.Initialize();

            try
            {
                using var device = GetFirstDeviceWithSystemTimestampSupport();
                if (device == null)
                {
                    throw new Exception("No compatible device found!");
                }

                // Configure device for freerun acquisition
                Configure(device);

                // Prepare and start acquisition
                using var dataStream = PrepareAndStartAcquisition(device);

                // Enable remote device events to demonstrate timestamp mapping
                using var eventController = EnableRemoteDeviceEventsIfPossible(device);

                int imageCount = 0;

                while (imageCount < IMAGE_COUNT_MAX)
                {
                    // Wait for a buffer to finish acquisition (timeout in ms)
                    var buffer = dataStream.WaitForFinishedBuffer(5000);

                    // Retrieve buffer system timestamp (ns since Unix epoch)
                    ulong systemTimestampNs = buffer.SystemTimestamp_ns();

                    Console.WriteLine("--Buffer--");
                    Console.WriteLine($"System timestamp [ns since epoch]: {systemTimestampNs}");

                    PrintStructuredTimestamp(systemTimestampNs, Time.Local);
                    PrintStructuredTimestamp(systemTimestampNs, Time.Utc);

                    if (eventController != null)
                    {
                        CalculateAndPrintRemoteDeviceEventSystemTimestamp(device, eventController);
                    }

                    // Return buffer to acquisition queue
                    dataStream.QueueBuffer(buffer);
                    imageCount++;
                }

                // Stop acquisition and release resources
                StopAcquisition(dataStream);
            }
            catch (Exception e)
            {
                Console.WriteLine("EXCEPTION: " + e.Message);
            }
            finally
            {
                // One call to `Close` is required for each call to `Initialize`.
                Library.Close();
            }
        }

        /// <summary>
        /// Select the first connected device that supports system timestamps.
        /// </summary>
        private static Device GetFirstDeviceWithSystemTimestampSupport()
        {
            var deviceManager = DeviceManager.Instance();
            deviceManager.Update();

            if (deviceManager.Devices().Count == 0)
            {
                Console.WriteLine("No camera found.");
                return null;
            }

            foreach (var descriptor in deviceManager.Devices())
            {
                var device = descriptor.OpenDevice(DeviceAccessType.Control);
                if (IsSystemTimestampSupported(device))
                {
                    return device;
                }

                device.Dispose();
            }

            Console.WriteLine("No device supports system timestamps.");
            return null;
        }

        /// <summary>
        /// Returns true if the device implements all nodes required for system timestamp support.
        /// </summary>
        private static bool IsSystemTimestampSupported(Device device)
        {
            var nodeMap = device.NodeMaps()[0];

            try
            {
                return nodeMap.FindNode<EnumerationNode>("SynchronizationTimestampMode").IsImplemented()
                    && nodeMap.FindNode<IntegerNode>("SynchronizationTimestampSystem").IsImplemented()
                    && nodeMap.FindNode<IntegerNode>("SynchronizationTimestampDevice").IsImplemented()
                    && nodeMap.FindNode<IntegerNode>("SynchronizationTimestampInterval").IsImplemented()
                    && nodeMap.FindNode<CommandNode>("SynchronizationTimestampLatch").IsImplemented();
            }
            catch
            {
                return false;
            }
        }

        /// <summary>
        /// Disables device trigger if available
        /// </summary>
        private static void DisableDeviceTrigger(NodeMap nodeMapRemoteDevice)
        {
            var requiredNodes = new List<string> { "TriggerSelector", "TriggerMode" };

            foreach (var node in requiredNodes)
            {
                if (!nodeMapRemoteDevice.HasNode(node))
                {
                    return;
                }
            }

            var nodeTriggerSelector = nodeMapRemoteDevice.FindNode<EnumerationNode>("TriggerSelector");
            var nodeTriggerMode = nodeMapRemoteDevice.FindNode<EnumerationNode>("TriggerMode");

            var triggerSelectorDisablePreference = new List<string> { "ExposureStart", "FrameStart" };

            foreach (var selectorValue in triggerSelectorDisablePreference)
            {
                if (nodeTriggerSelector.HasEntry(selectorValue))
                {
                    nodeTriggerSelector.SetCurrentEntry(selectorValue);
                    nodeTriggerMode.SetCurrentEntry("Off");
                    break;
                }
            }
        }

        /// <summary>
        /// Configure the device for freerun acquisition.
        /// Triggers are disabled if loading default UserSet fails.
        /// </summary>
        private static void Configure(Device device)
        {
            var nodeMapRemote = device.RemoteDevice().NodeMaps()[0];

            try
            {
                nodeMapRemote.FindNode<EnumerationNode>("UserSetSelector").SetCurrentEntry("Default");
                nodeMapRemote.FindNode<CommandNode>("UserSetLoad").Execute();
                nodeMapRemote.FindNode<CommandNode>("UserSetLoad").WaitUntilDone();
            }
            catch
            {
                Console.WriteLine("Failed to load UserSet Default. Manual freerun configuration.");

                DisableDeviceTrigger(nodeMapRemote);
            }
        }

        /// <summary>
        /// Prepare and start data stream acquisition.
        /// Allocates buffers and locks critical parameters.
        /// </summary>
        private static DataStream PrepareAndStartAcquisition(Device device)
        {
            var dataStream = device.DataStreams()[0].OpenDataStream();
            var nodeMapRemote = device.RemoteDevice().NodeMaps()[0];

            var payloadSize = nodeMapRemote.FindNode<IntegerNode>("PayloadSize").Value();
            ulong minBuffers = dataStream.NumBuffersAnnouncedMinRequired();

            for (ulong i = 0; i < minBuffers; i++)
            {
                var buffer = dataStream.AllocAndAnnounceBuffer((uint) payloadSize, IntPtr.Zero);
                dataStream.QueueBuffer(buffer);
            }

            nodeMapRemote.FindNode<IntegerNode>("TLParamsLocked").SetValue(1);

            dataStream.StartAcquisition(AcquisitionStartMode.Default);
            nodeMapRemote.FindNode<CommandNode>("AcquisitionStart").Execute();

            return dataStream;
        }

        /// <summary>
        /// Enable remote device events if supported.
        /// </summary>
        private static EventController EnableRemoteDeviceEventsIfPossible(Device device)
        {
            try
            {
                var nodeMapRemote = device.RemoteDevice().NodeMaps()[0];
                nodeMapRemote.FindNode<EnumerationNode>("EventSelector").SetCurrentEntry("ExposureStart");
                nodeMapRemote.FindNode<EnumerationNode>("EventNotification").SetCurrentEntry("On");

                return device.EnableEvents(EventType.RemoteDevice);
            }
            catch
            {
                return null;
            }
        }

        /// <summary>
        /// Calculate and print system timestamp of a remote device event.
        /// </summary>
        private static void CalculateAndPrintRemoteDeviceEventSystemTimestamp(Device device, EventController eventController)
        {
            var nodeMapRemote = device.RemoteDevice().NodeMaps()[0];

            var ev = eventController.WaitForEvent(5000);
            nodeMapRemote.UpdateEventNodes(ev);

            var eventTimestampNs = (ulong) nodeMapRemote.FindNode<IntegerNode>("EventExposureStartTimestamp").Value();
            var nodeMapDevice = device.NodeMaps()[0];

            var latch = nodeMapDevice.FindNode<CommandNode>("SynchronizationTimestampLatch");
            latch.Execute();
            latch.WaitUntilDone();

            var systemTimestampNs = (ulong) nodeMapDevice.FindNode<IntegerNode>("SynchronizationTimestampSystem").Value();
            var deviceTimestampNs = (ulong) nodeMapDevice.FindNode<IntegerNode>("SynchronizationTimestampDevice").Value();
            var eventSystemTimestampNs = systemTimestampNs + (eventTimestampNs - deviceTimestampNs);

            Console.WriteLine("--ExposureStartEvent--");
            Console.WriteLine($"Timestamp [ns]: {eventTimestampNs}");
            Console.WriteLine($"System timestamp [ns since epoch]: {eventSystemTimestampNs}");

            PrintStructuredTimestamp(eventSystemTimestampNs, Time.Local);
            PrintStructuredTimestamp(eventSystemTimestampNs, Time.Utc);
        }

        /// <summary>
        /// Stop acquisition and release all buffers.
        /// Unlock previously locked parameters.
        /// </summary>
        private static void StopAcquisition(DataStream dataStream)
        {
            var nodeMapRemote = dataStream.ParentDevice().RemoteDevice().NodeMaps()[0];

            dataStream.StopAcquisition(AcquisitionStopMode.Default);
            nodeMapRemote.FindNode<CommandNode>("AcquisitionStop").Execute();

            nodeMapRemote.FindNode<IntegerNode>("TLParamsLocked").SetValue(0);

            dataStream.Flush(DataStreamFlushMode.DiscardAll);
            foreach (var buffer in dataStream.AnnouncedBuffers())
            {
                dataStream.RevokeBuffer(buffer);
            }
        }

        private enum Time
        {
            Local,
            Utc
        }

        /// <summary>
        /// Print structured timestamp in human-readable form.
        /// Accepts timestamps in nanoseconds since Unix epoch.
        /// </summary>
        private static void PrintStructuredTimestamp(ulong timestampNs, Time time)
        {
            ulong seconds = timestampNs / 1_000_000_000;
            ulong nanosecondsAfterSeconds = timestampNs % 1_000_000_000;

            ulong milliseconds = nanosecondsAfterSeconds / 1_000_000;
            ulong microseconds = (nanosecondsAfterSeconds / 1_000) % 1_000;
            ulong nanoseconds = nanosecondsAfterSeconds % 1_000;

            bool useUtc = (time == Time.Utc);

            DateTime dt = useUtc
                ? DateTimeOffset.FromUnixTimeSeconds((long) seconds).UtcDateTime
                : DateTimeOffset.FromUnixTimeSeconds((long) seconds).LocalDateTime;

            string label = useUtc ? "[UTC]" : "[Local]";
            Console.WriteLine(
                $"Structured timestamp: {label} {dt:yyyy-MM-dd HH:mm:ss}:{milliseconds}:{microseconds}:{nanoseconds}"
            );
        }
    }
}
