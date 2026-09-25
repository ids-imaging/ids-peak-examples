/*
 * Copyright(C) 2026, IDS Imaging Development Systems GmbH.
 *
 * Permission to use, copy, modify, and/or distribute this software for
 * any purpose with or without fee is hereby granted.
 *
 * THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
 * WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
 * FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
 * DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
 * AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
 * OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

/*
 * This example shows how to configure and use Precision Time Protocol (PTP)
 * with connected GigE cameras.
 */

#include <algorithm>
#include <iostream>
#include <memory>
#include <vector>

#include <peak/peak.hpp>

namespace
{
struct DeviceContext
{
    std::shared_ptr<peak::core::Device> device;
    std::shared_ptr<peak::core::DataStream> dataStream;
};

} // namespace

int main()
{
    std::vector<DeviceContext> deviceList{};

    try
    {
        constexpr size_t buffersToAcquire = 10;

        // Initialize library
        peak::Library::Initialize();

        // Find and open all available GEV cameras with control access
        {
            // Initialize DeviceManager and update device list
            auto& deviceManager = peak::DeviceManager::Instance();
            deviceManager.Update();

            const auto filteredDevices = deviceManager.FindDevices(
                [](const std::shared_ptr<peak::core::DeviceDescriptor>& descriptor) {
                    return descriptor->IsOpenable(peak::core::DeviceAccessType::Control)
                        && descriptor->TLType() == "GEV";
                });

            if (filteredDevices.empty())
            {
                std::cerr << "Failed to find any openable camera!" << std::endl;
                peak::Library::Close();
                return -1;
            }

            if (filteredDevices.size() < 2)
            {
                std::cerr << "At least two cameras are required for PTP synchronization!" << std::endl;
                peak::Library::Close();
                return -1;
            }

            std::cout << "Opening " << filteredDevices.size() << " available devices...\n";
            for (const auto& dev : filteredDevices)
            {
                DeviceContext context;
                context.device = dev->OpenDevice(peak::core::DeviceAccessType::Control);
                context.dataStream = context.device->DataStreams().at(0)->OpenDataStream();
                deviceList.push_back(context);
            }
            std::cout << "Opened " << deviceList.size() << " devices.\n";
        }

        bool isSlaveOnly = false;
        // Configure PTP and acquisition for each device
        for (const auto& currentDevice : deviceList)
        {
            std::cout << "Configuring device " << currentDevice.device->DisplayName() << "...\n";

            const auto nodeMapRemoteDevice = currentDevice.device->RemoteDevice()->NodeMaps().at(0);

            // Enable PTP for all devices
            nodeMapRemoteDevice->FindNode<peak::core::nodes::BooleanNode>("PtpSlaveOnly")->SetValue(isSlaveOnly);
            nodeMapRemoteDevice->FindNode<peak::core::nodes::BooleanNode>("PtpEnable")->SetValue(true);
            // Configure first device as master and remaining devices as slave only
            isSlaveOnly = true;
        }

        // Wait until every device has synchronized to the master clock
        std::cout << "Waiting for all devices to synchronize to the master clock. This could take a few seconds...\n";
        bool isMaster = true;
        for (const auto& currentDevice : deviceList)
        {
            const auto nodeMapRemoteDevice = currentDevice.device->RemoteDevice()->NodeMaps().at(0);
            const auto ptpStatus = nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("PtpStatus");

            const std::string requiredStatus = isMaster ? "Master" : "Slave";
            while (true)
            {
                // Note: Due to a problem with caching the PtpStatus Node is read ignoring cached values.
                const auto status = ptpStatus->CurrentEntry(peak::core::nodes::NodeCacheUsePolicy::IgnoreCache)
                                        ->SymbolicValue();
                if (status == "Faulty")
                {
                    std::cerr << "Error: PTP synchronization failed for device " << currentDevice.device->DisplayName()
                              << " (status: Faulty)." << std::endl;
                    peak::Library::Close();
                    return -1;
                }
                if (status == "Disabled")
                {
                    std::cerr << "Error: PTP is disabled for device " << currentDevice.device->DisplayName()
                              << " (status: Disabled)." << std::endl;
                    peak::Library::Close();
                    return -1;
                }
                if (status == requiredStatus)
                {
                    break;
                }
                std::this_thread::sleep_for(std::chrono::seconds(1));
            }
            isMaster = false;
        }
        std::cout << "All devices synchronized to the master clock.\n";

        // Configure PPS (Pulses per second) trigger which is synchronized using PTP
        for (const auto& currentDevice : deviceList)
        {
            const auto nodeMapRemoteDevice = currentDevice.device->RemoteDevice()->NodeMaps().at(0);

            // Set the Trigger source for ExposureStart to SignalMultiplier0
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("TriggerSelector")
                ->SetCurrentEntry("ExposureStart");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("TriggerSource")
                ->SetCurrentEntry("SignalMultiplier0");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("TriggerMode")->SetCurrentEntry("On");

            // Configure SignalMultiplier0 to use PPS as signal source
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("SignalMultiplierSelector")
                ->SetCurrentEntry("SignalMultiplier0");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("SignalMultiplierSource")
                ->SetCurrentEntry("PPS");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("SignalMultiplierValue")->SetValue(1);
            nodeMapRemoteDevice->FindNode<peak::core::nodes::BooleanNode>("SignalMultiplierEnable")->SetValue(true);

            // Prepare devices for acquisition
            // Lock transport layer parameters (TLParamsLocked = 1) to
            // prevent irregular access to the remote device during acquisition
            nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(1);

            // Get the required payload size. If the data stream does not
            // define it, fall back to the remote device node map.
            const auto payloadSize = currentDevice.dataStream->DefinesPayloadSize() ?
                currentDevice.dataStream->PayloadSize() :
                static_cast<size_t>(
                    nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("PayloadSize")->Value());

            const auto bufferCount = std::max(
                currentDevice.dataStream->NumBuffersAnnouncedMinRequired(), buffersToAcquire);
            currentDevice.dataStream->AddAcquisitionBuffers(payloadSize, bufferCount);

            // Start acquisition on both the data stream and device
            currentDevice.dataStream->StartAcquisition(peak::core::AcquisitionStartMode::Default, buffersToAcquire);
        }

        // Start acquisition for every device
        for (const auto& currentDevice : deviceList)
        {
            const auto nodeMapRemoteDevice = currentDevice.device->RemoteDevice()->NodeMaps().at(0);
            // Do not wait for command completion so subsequent devices can start sooner
            nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("AcquisitionStart")->Execute();
        }

        std::cout << "Acquisition started. Capturing " << buffersToAcquire << " buffers per device...\n";

        for (size_t deviceIndex = 0; deviceIndex < deviceList.size(); ++deviceIndex)
        {
            const auto& currentDevice = deviceList.at(deviceIndex);
            std::cout << currentDevice.device->DisplayName();
            if (deviceIndex == 0)
            {
                std::cout << " - Master";
            }
            std::cout << ":\n";
            for (size_t frameIndex = 0; frameIndex < buffersToAcquire; ++frameIndex)
            {
                try
                {
                    // Wait for a filled buffer (timeout: 5000 milliseconds)
                    const auto buffer = peak::core::BufferGuard(currentDevice.dataStream->WaitForFinishedBuffer(5'000));

                    std::cout << "Buffer " << (frameIndex + 1) << " Timestamp: " << buffer->Timestamp_ns() << "\n";
                }
                catch (const std::exception& e)
                {
                    std::cerr << "Warning: Failed to get buffer " << (frameIndex + 1) << " from device "
                              << currentDevice.device->DisplayName() << ": " << e.what() << "\n";
                }
            }
            std::cout << "\n";
        }

        // Stop acquisition and free buffers
        for (const auto& currentDevice : deviceList)
        {
            const auto nodeMapRemoteDevice = currentDevice.device->RemoteDevice()->NodeMaps().at(0);

            // Stop acquisition on both data stream and device
            currentDevice.dataStream->StopAcquisition(peak::core::AcquisitionStopMode::Default);
            nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("AcquisitionStop")->ExecuteAndWait();

            // Unlock transport layer parameters (TLParamsLocked = 0) to allow
            // access to the remote device again
            nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(0);

            // revoke all buffers
            currentDevice.dataStream->FlushAndRevokeAllBuffers();
        }
    }
    catch (const std::exception& e)
    {
        std::cerr << "Error: " << e.what() << std::endl;
    }

    try
    {
        // Close library
        peak::Library::Close();
    }
    catch (const std::exception& e)
    {
        std::cerr << "Error: " << e.what() << std::endl;
    }

    return 0;
}
