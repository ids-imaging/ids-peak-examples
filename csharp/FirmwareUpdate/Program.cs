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
using System.Linq;
using System.Collections.Generic;

using IDSImaging.Peak.API;
using IDSImaging.Peak.API.Core;

namespace IDSImaging.Peak.Samples.FirmwareUpdate
{
    internal struct DeviceUpdateInformation
    {
        public DeviceDescriptor Device;
        public FirmwareUpdateInformation UpdateInformation;
    };

    /// <summary>
    /// This example demonstrates how to programmatically update the firmware of
    /// connected devices using the IDS peak generic API.
    /// </summary>
    /// <remarks>
    /// <para>
    /// The application:
    /// <list type="bullet">
    /// <item><description>Detects available GenTL devices using the DeviceManager</description></item>
    /// <item><description>Identifies devices compatible with the provided firmware file (GUF)</description></item>
    /// <item><description>Prompts the user for confirmation before updating</description></item>
    /// <item><description>Executes the firmware update process</description></item>
    /// <item><description>Reports update progress via callback functions</description></item>
    /// </list>
    /// </para>
    /// <para>
    /// Progress callbacks provide information about update start, progress,
    /// individual update steps, successful completion, or failure.
    ///</para>
    /// <para>
    /// The firmware file must be provided as a command line argument in the
    /// Generic Update Format (GUF).
    /// </para>
    /// <example><code>FirmwareUpdate.exe firmware_file.guf</code></example>
    /// </remarks>
    internal static class Program
    {
        private static int Main(string[] args)
        {
            if (args.Length != 1)
            {
                Console.WriteLine("Wrong number of arguments! Usage: firmware_update_csharp <gufPath>");
                return -1;
            }

            // The library must be initialized before use.
            // Each `Initialize` call must be matched with a corresponding call
            // to `Close`.
            Library.Initialize();

            try
            {
                var gufPath = args[0];
                var deviceManager = DeviceManager.Instance();

                // Update the device manager.
                // When `Update` is called, it searches for all producer libraries
                // contained in the directories found in the official GenICam GenTL
                // environment variable GENICAM_GENTL{32/64}_PATH. It then opens all
                // found ProducerLibraries, their Systems, their Interfaces, and lists
                // all available DeviceDescriptors.
                deviceManager.Update();

                if (deviceManager.Devices().IsEmpty)
                {
                    Console.WriteLine("No device found. Exiting program.");
                    return 0;
                }

                var updater = new FirmwareUpdater();
                // Get a list of devices compatible with the firmware file.
                DeviceUpdateInformation[] compatibleDeviceUpdates =
                    FindCompatibleDevices(deviceManager, updater, gufPath);

                if (compatibleDeviceUpdates.Length == 0)
                {
                    Console.WriteLine("No compatible devices found.");
                    return 0;
                }

                Console.WriteLine("The following devices will be updated:");
                foreach (var update in compatibleDeviceUpdates)
                {
                    Console.WriteLine($"\t {update.Device.ModelName()}({update.Device.SerialNumber()})");
                }

                Console.Write("Continue? y/n: ");
                var answer = Console.Read();

                if (answer != 'y')
                {
                    Console.WriteLine("Update aborted!");
                    return 0;
                }

                foreach (var update in compatibleDeviceUpdates)
                {
                    // NOTE: `UpdateDevice` is a blocking call. We construct an
                    //       observer and register callbacks to be notified about
                    //       the update progress.
                    var observer = new FirmwareUpdateProgressObserver();
                    RegisterObserverCallbacks(observer, update);

                    updater.UpdateDevice(update.Device, update.UpdateInformation, observer);
                }
            }
            catch (Exception e)
            {
                Console.WriteLine("Exception: " + e.Message);
            }
            finally
            {
                // Each `Initialize` call must be matched with a corresponding call
                // to `Close`.
                Library.Close();
            }

            return 0;
        }

        private static void RegisterObserverCallbacks(FirmwareUpdateProgressObserver observer,
            DeviceUpdateInformation update)
        {
            // Copy model and serial number early, since the device object will
            // become invalid after the update starts.
            var modelName = update.Device.ModelName().Clone();
            var serialNumber = update.Device.SerialNumber().Clone();

            // Called once at the beginning of the firmware update process.
            // `updateInformation` includes firmware metadata like Version and Description, among other details.
            observer.UpdateStartedEvent +=
                (object sender, FirmwareUpdateInformation updateInformation, uint estimatedDurationMs) =>
                    Console.WriteLine(
                        $"Updating {modelName} ({serialNumber}) to version {updateInformation.Version()}");

            // Called once when the firmware update completes successfully.
            observer.UpdateFinishedEvent += (object sender) =>
                Console.WriteLine($"Finished updating {modelName} ({serialNumber})");

            // Called if the firmware update fails at any point.
            // The `errorDescription` parameter provides details on why the update failed.
            observer.UpdateFailedEvent += (object sender, string errorDescription) =>
                Console.WriteLine($"Updating failed {modelName} ({serialNumber}): {errorDescription}");

            // Called at the start of each update step (e.g., reboot, or write).
            // Includes step type, estimated duration, and a human-readable description.
            observer.UpdateStepStartedEvent +=
                (object sender, FirmwareUpdateStep updateStep, uint estimatedDurationMs, string description) =>
                    Console.WriteLine($"{modelName} ({serialNumber}) | {updateStep.ToString()} | {description}");

            // Called periodically to report the progress percentage (0–100%) of the current update step.
            observer.UpdateStepProgressChangedEvent +=
                (object sender, FirmwareUpdateStep updateStep, double progressPercentage) =>
                {
                    Console.Write($"\r\tProgress: {progressPercentage:F2}%");
                    if (progressPercentage >= 100)
                    {
                        Console.WriteLine();
                    }
                };

            // NOTE: You can also register for `UpdateStepFinishedEvent` for even more granular step tracking.
            // observer.UpdateStepFinishedEvent += ...
        }

        private static DeviceUpdateInformation[] FindCompatibleDevices(DeviceManager deviceManager,
            FirmwareUpdater updater, string gufPath)
        {
            var compatibleDeviceUpdates = new List<DeviceUpdateInformation>();

            foreach (var device in deviceManager.Devices())
            {
                // Only proceed with devices that are openable with control-level access.
                // This ensures the device can be accessed for firmware operations.
                if (!device.IsOpenable(DeviceAccessType.Control))
                {
                    Console.WriteLine("Skipped device " + device.ModelName() + " ("
                                      + device.SerialNumber() + "), since it could not be opened!");
                    continue;
                }

                // Skip devices we've already added. Devices can appear multiple times
                // if exposed through different transport layers or interfaces (e.g., USB + GigE).
                var isDeviceAlreadyAdded =
                    compatibleDeviceUpdates.Exists(u => device.SerialNumber() == u.Device.SerialNumber());
                if (isDeviceAlreadyAdded)
                {
                    continue;
                }

                // Query the updater for update information compatible with the device.
                // If the list is empty, the GUF file does not apply to this device.
                var updateInformationList = updater.CollectFirmwareUpdateInformation(gufPath, device);
                if (updateInformationList.IsEmpty)
                {
                    continue;
                }

                // Select the latest available firmware update entry for the device.
                var latestUpdateInformation = updateInformationList.First();

                // Store the device along with its matching firmware update information.
                DeviceUpdateInformation updateInformation;
                updateInformation.Device = device;
                updateInformation.UpdateInformation = latestUpdateInformation;

                compatibleDeviceUpdates.Add(updateInformation);
            }

            return compatibleDeviceUpdates.ToArray();
        }
    }
}
