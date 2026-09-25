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
#include <chrono>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

#include <peak/peak.hpp>

namespace
{
struct DeviceContext
{
    std::shared_ptr<peak::core::Device> device;
    std::shared_ptr<peak::core::DataStream> dataStream;
};

std::vector<DeviceContext> OpenAllAvailableGevCameras();
void StopAcquisitionAndRevokeBuffers(const std::vector<DeviceContext>& deviceList);
} // namespace

int main()
{
    int exitCode = 0;

    try
    {
        constexpr size_t buffersToAcquire = 10;

        // Initialize library
        peak::Library::Initialize();

        // Find and open all available GEV cameras with control access
        const auto deviceList = OpenAllAvailableGevCameras();

        // The first camera is the only opened camera eligible to become master.
        // It is expected to be elected unless an external grandmaster is present
        // and wins the Best Master Clock Algorithm (BMCA) election.
        bool isSlaveOnly = false;
        for (const auto& currentDevice : deviceList)
        {
            std::cout << "Configuring device " << currentDevice.device->DisplayName() << "...\n";

            const auto nodeMapRemoteDevice = currentDevice.device->RemoteDevice()->NodeMaps().at(0);

            // Enable PTP for all devices
            nodeMapRemoteDevice->FindNode<peak::core::nodes::BooleanNode>("PtpSlaveOnly")->SetValue(isSlaveOnly);
            nodeMapRemoteDevice->FindNode<peak::core::nodes::BooleanNode>("PtpEnable")->SetValue(true);
            isSlaveOnly = true;
        }

        // The first camera can become either Master or Slave; slave-only cameras
        // must become Slave. Allow time for PTP election and synchronization.
        std::cout << "Waiting for all devices to synchronize to the PTP grandmaster... This could take more than 30 "
                     "seconds...\n";
        constexpr auto ptpSynchronizationTimeout = std::chrono::seconds(60);
        const auto synchronizationDeadline = std::chrono::steady_clock::now() + ptpSynchronizationTimeout;
        std::vector<std::string> ptpStatusByDevice{};
        bool isFirstCamera = true;
        for (const auto& currentDevice : deviceList)
        {
            const auto nodeMapRemoteDevice = currentDevice.device->RemoteDevice()->NodeMaps().at(0);
            const auto ptpDataSetLatch = nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>(
                "PtpDataSetLatch");
            const auto ptpStatus = nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("PtpStatus");
            const std::string expectedStatus = isFirstCamera ? "Master or Slave" : "Slave";

            while (true)
            {
                // We need to latch the PTP data set to get a consistent view of the PTP status.
                ptpDataSetLatch->ExecuteAndWait();

                // Retrieve the latched value of the PTP status.
                const auto status = ptpStatus->CurrentEntry()->SymbolicValue();
                if (status == "Faulty")
                {
                    throw std::runtime_error("PTP synchronization failed for device "
                        + currentDevice.device->DisplayName() + " (status: Faulty).");
                }
                if (status == "Disabled")
                {
                    throw std::runtime_error(
                        "PTP is disabled for device " + currentDevice.device->DisplayName() + " (status: Disabled).");
                }

                const bool hasSynchronized = isFirstCamera ? (status == "Master" || status == "Slave") :
                                                             status == "Slave";
                if (hasSynchronized)
                {
                    ptpStatusByDevice.push_back(status);
                    break;
                }

                if (std::chrono::steady_clock::now() >= synchronizationDeadline)
                {
                    throw std::runtime_error("Timed out waiting for device " + currentDevice.device->DisplayName()
                        + " to reach PTP status " + expectedStatus + " (last status: " + status + ").");
                }

                std::this_thread::sleep_for(std::chrono::seconds(1));
            }

            isFirstCamera = false;
        }

        std::cout << "All devices synchronized to the PTP grandmaster.\n";

        const auto masterDevice = std::find(ptpStatusByDevice.begin(), ptpStatusByDevice.end(), "Master");
        if (masterDevice == ptpStatusByDevice.end())
        {
            std::cout << "No opened camera is the master; the grandmaster is outside the opened camera list.\n";
        }
        else
        {
            const auto masterDeviceIndex = static_cast<size_t>(std::distance(ptpStatusByDevice.begin(), masterDevice));
            std::cout << deviceList.at(masterDeviceIndex).device->DisplayName() << " was elected master.\n";
        }

        // Configure pulse per second (PPS) trigger which is synchronized using PTP
        for (const auto& currentDevice : deviceList)
        {
            const auto nodeMapRemoteDevice = currentDevice.device->RemoteDevice()->NodeMaps().at(0);

            // Set the Trigger source for `ExposureStart` to `SignalMultiplier0`
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("TriggerSelector")
                ->SetCurrentEntry("ExposureStart");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("TriggerSource")
                ->SetCurrentEntry("SignalMultiplier0");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("TriggerMode")->SetCurrentEntry("On");

            // Configure `SignalMultiplier0` to use PPS as signal source
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("SignalMultiplierSelector")
                ->SetCurrentEntry("SignalMultiplier0");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("SignalMultiplierSource")
                ->SetCurrentEntry("PPS");
            // The `SignalMultiplierValue`, in the case of PPS, controls the number of
            // times an image is triggered per second.
            // Note that extreme values may lead to the last trigger before
            // the next second being skipped, resulting in fewer images than expected.
            //
            // This value also interacts with the exposure time.
            // If the exposure time is longer than the time between triggers,
            // the camera will not be able to trigger at the expected rate.
            nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("SignalMultiplierValue")->SetValue(1);
            nodeMapRemoteDevice->FindNode<peak::core::nodes::BooleanNode>("SignalMultiplierEnable")->SetValue(true);

            // NOTE: The configured trigger can be combined with
            //       trigger settings such as `TriggerDelay` and
            //       `TriggerDivider` to further control the timing of the
            //       trigger events (e.g. a multiplier value of 5 and divider
            //       value of 2 give a nominal rate of 2.5 triggers per second).

            // The timestamp that is attached to each buffer corresponds to
            // the time of the `ReadOutStart` event, which is when the
            // data read out of the sensor starts.
            // Thus, the timestamp is influenced by the exposure time,
            // which is the time between the `ExposureStart` and `ReadOutStart` events.
            // Set the exposure time to a fixed value to get more similar timestamps for all cameras.
            constexpr auto exposureTime = std::chrono::milliseconds{ 10 };
            constexpr auto exposureTimeUs = std::chrono::duration_cast<std::chrono::microseconds>(exposureTime).count();
            nodeMapRemoteDevice->FindNode<peak::core::nodes::FloatNode>("ExposureTime")->SetValue(exposureTimeUs);

            // Enable timestamp chunk data to be able to read the timestamp from the buffer.
            // The `ChunkTimestamp` corresponds to the `ExposureStart` event,
            // which is the time when the exposure of the sensor starts.
            nodeMapRemoteDevice->FindNode<peak::core::nodes::BooleanNode>("ChunkModeActive")->SetValue(true);
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("ChunkSelector")
                ->SetCurrentEntry("Timestamp");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::BooleanNode>("ChunkEnable")->SetValue(true);

            // Prepare devices for acquisition
            // Lock transport layer parameters (`TLParamsLocked` = 1) to
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

            // Start acquisition on the data stream.
            // Supply the number of buffers to acquire so the DataStream
            // automatically stops acquisition after the specified number
            // of buffers has been acquired.
            currentDevice.dataStream->StartAcquisition(peak::core::AcquisitionStartMode::Default, buffersToAcquire);
        }

        // Start acquisition for every device after the device has been configured. By keeping the
        // `AcquisitionStart` command separate from the data stream acquisition start, we minimize the
        // delay between devices, reducing the likelihood that a configured trigger is received by
        // some cameras before the others are ready.
        //
        // NOTE: `AcquisitionStart` is sent to devices one after another. While later cameras are still
        // starting, an incoming PPS edge can already trigger cameras that are running. As a result,
        // some cameras may respond to a PPS trigger one cycle before others. In practice, it can take
        // a few frames until all cameras are running and reacting to the same PPS pulse sequence.
        // When evaluating synchronization quality, it is therefore recommended to ignore the first
        // frames after startup and use subsequent frames once all cameras are stably running.
        for (const auto& currentDevice : deviceList)
        {
            const auto nodeMapRemoteDevice = currentDevice.device->RemoteDevice()->NodeMaps().at(0);
            // Do not wait for command completion so subsequent devices can start sooner
            nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("AcquisitionStart")->Execute();
        }

        std::cout << "Acquisition started. Capturing " << buffersToAcquire << " buffers per device...\n\n";

        auto ptpStatus = ptpStatusByDevice.cbegin();
        for (const auto& currentDevice : deviceList)
        {
            std::cout << currentDevice.device->DisplayName() << " - PTP " << *ptpStatus << ":\n";
            ++ptpStatus;

            const auto nodeMapRemoteDevice = currentDevice.device->RemoteDevice()->NodeMaps().at(0);

            for (size_t frameIndex = 0; frameIndex < buffersToAcquire; ++frameIndex)
            {
                try
                {
                    // Wait for a filled buffer (timeout: 5000 milliseconds)
                    const auto buffer = peak::core::BufferGuard(currentDevice.dataStream->WaitForFinishedBuffer(5'000));

                    const auto readoutStartTimestamp = buffer->Timestamp_ns();

                    // Get the value of the timestamp chunk data from the buffer.
                    // This timestamp corresponds to the `ExposureStart` event.
                    nodeMapRemoteDevice->UpdateChunkNodes(buffer.Buffer());
                    const auto exposureStartTimestamp =
                        nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("ChunkTimestamp")->Value();

                    // NOTE: Without PTP, the GigE Vision timestamp counter is free-running at a
                    // device-specific rate. With PTP enabled, PTP controls the counter, mapping
                    // PTP-synchronized time from IEEE 1588`s 80-bit timestamp to GigE Vision`s
                    // 64-bit signed representation. Buffer timestamps then reflect that
                    // PTP-synchronized value instead of the free-running count.
                    //
                    // Also note that the resulting buffer timestamps (`ReadOutStart`)
                    // are influenced by multiple factors, including exposure time,
                    // the width/height of the image, as well as the
                    // camera`s internal processing and sensor type (e.g. rolling vs global shutter).
                    std::cout << "Buffer " << std::setfill('0') << std::setw(2) << (frameIndex + 1)
                              << " Timestamp ReadOutStart [ns]: " << readoutStartTimestamp << ";"
                              << " Timestamp ExposureStart [ns]: " << exposureStartTimestamp << "\n";
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
        StopAcquisitionAndRevokeBuffers(deviceList);
    }
    catch (const std::exception& e)
    {
        std::cerr << "Error: " << e.what() << std::endl;
        exitCode = -1;
    }

    try
    {
        // Close library
        peak::Library::Close();
    }
    catch (const std::exception& e)
    {
        std::cerr << "Error: " << e.what() << std::endl;
        exitCode = -1;
    }

    return exitCode;
}

namespace
{

std::vector<DeviceContext> OpenAllAvailableGevCameras()
{
    // Initialize DeviceManager and update device list
    auto& deviceManager = peak::DeviceManager::Instance();
    deviceManager.Update();
    std::vector<DeviceContext> deviceList{};

    const auto filteredDevices = deviceManager.FindDevices(
        [](const std::shared_ptr<peak::core::DeviceDescriptor>& descriptor) {
            return descriptor->IsOpenable(peak::core::DeviceAccessType::Control) && descriptor->TLType() == "GEV";
        });

    if (filteredDevices.empty())
    {
        throw std::runtime_error("Failed to find any openable camera!");
    }

    if (filteredDevices.size() < 2)
    {
        throw std::runtime_error("At least two cameras are required for PTP synchronization!");
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

    return deviceList;
}

void StopAcquisitionAndRevokeBuffers(const std::vector<DeviceContext>& deviceList)
{
    for (const auto& currentDevice : deviceList)
    {
        const auto nodeMapRemoteDevice = currentDevice.device->RemoteDevice()->NodeMaps().at(0);

        // Stop acquisition on both data stream and device
        nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("AcquisitionStop")->ExecuteAndWait();
        currentDevice.dataStream->StopAcquisition(peak::core::AcquisitionStopMode::Default);

        // Unlock transport layer parameters (`TLParamsLocked` = 0) to allow
        // access to the remote device again
        nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(0);

        // Revoke all buffers
        currentDevice.dataStream->FlushAndRevokeAllBuffers();
    }
}
} // namespace
