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

#include <peak/peak.hpp>

#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <memory>

std::shared_ptr<peak::core::Device> GetFirstDeviceWithSystemTimestampSupport();

void DisableDeviceTrigger(const std::shared_ptr<peak::core::NodeMap>& nodeMapRemoteDevice);

void Configure(const std::shared_ptr<peak::core::Device>& device);

std::shared_ptr<peak::core::DataStream> PrepareAndStartAcquisition(const std::shared_ptr<peak::core::Device>& device);

std::unique_ptr<peak::core::EventController> EnableRemoteDeviceEventsIfPossible(
    const std::shared_ptr<peak::core::Device>& device);

void CalculateAndPrintRemoteDeviceEventSystemTimestamp(const std::shared_ptr<peak::core::Device>& device,
    const std::unique_ptr<peak::core::EventController>& remoteDeviceEventController);

void StopAcquisition(const std::shared_ptr<peak::core::DataStream>& dataStream);

bool IsSystemTimestampSupported(const std::shared_ptr<peak::core::Device>& device);

enum class Time
{
    Local,
    Utc
};

void PrintStructuredTimestamp(std::uint64_t timestampTimeSinceEpochNs, Time time);

int main()
{
    try
    {
        peak::Library::Initialize();

        const auto device = GetFirstDeviceWithSystemTimestampSupport();
        if (!device)
        {
            throw std::runtime_error{ "No compatible device found!" };
        }

        // Configure device for freerun acquisition (disables triggers if needed)
        Configure(device);

        // Allocate buffers, start the acquisition on the data stream and remote device
        const auto dataStream = PrepareAndStartAcquisition(device);

        // The following code is not related to buffer system timestamp functionality. We just enable remote device
        // events here to show how a user can calculate the event system timestamp given a normal event timestamp.
        const auto remoteDeviceEventController = EnableRemoteDeviceEventsIfPossible(device);

        constexpr auto imageCountMax = std::uint64_t{ 10 };
        auto imageCount = std::uint64_t{ 0 };
        while (imageCount < imageCountMax)
        {
            using namespace std::chrono_literals;

            // Wait for a buffer to finish acquisition
            auto buffer = dataStream->WaitForFinishedBuffer(5'000ms);

            // Retrieve and print the buffer's system timestamp
            // The timestamp is expressed in nanoseconds since Unix epoch
            // Note: The system timestamp is synchronized from the device timestamp and may have limited precision
            {
                const auto systemTimestampNs = buffer->SystemTimestamp_ns();
                std::cout << "--Buffer--" << '\n';
                std::cout << "System timestamp [time since epoch in ns]: " << systemTimestampNs << '\n';
                PrintStructuredTimestamp(systemTimestampNs, Time::Local);
                PrintStructuredTimestamp(systemTimestampNs, Time::Utc);
            }

            if (remoteDeviceEventController)
            {
                // Example: Map remote device event timestamps to system time
                CalculateAndPrintRemoteDeviceEventSystemTimestamp(device, remoteDeviceEventController);
            }

            // Return the buffer to the acquisition queue
            dataStream->QueueBuffer(buffer);
            ++imageCount;
        }
        std::cout << std::endl << std::endl;

        // Stop acquisition and release resources
        StopAcquisition(dataStream);

        peak::Library::Close();

        return EXIT_SUCCESS;
    }
    catch (const std::exception& e)
    {
        std::cout << "EXCEPTION: " << e.what() << std::endl;
        try
        {
            peak::Library::Close();
        }
        catch (const std::exception&)
        {
            std::cout << "EXCEPTION: Unable to close library." << std::endl;
        }

        return EXIT_FAILURE;
    }
}

/*
 * Select the first connected device that implements system timestamp nodes.
 * Returns nullptr if no compatible device is found.
 */
std::shared_ptr<peak::core::Device> GetFirstDeviceWithSystemTimestampSupport()
{
    // create a camera manager object
    auto& deviceManager = peak::DeviceManager::Instance();

    // update the device manager
    deviceManager.Update();

    // exit program if no camera was found
    if (deviceManager.Devices().empty())
    {
        std::cout << "No camera found. Exiting program." << std::endl << std::endl;
        return nullptr;
    }

    for (const auto& deviceDescriptor : deviceManager.Devices())
    {
        auto device = deviceDescriptor->OpenDevice(peak::core::DeviceAccessType::Control);
        if (IsSystemTimestampSupported(device))
        {
            return device;
        }
    }

    return nullptr;
}

void DisableDeviceTrigger(const std::shared_ptr<peak::core::NodeMap>& nodeMapRemoteDevice)
{
    const std::vector<std::string> requiredNodes = { "TriggerSelector", "TriggerMode" };
    for (const auto& node : requiredNodes)
    {
        if (!nodeMapRemoteDevice->HasNode(node))
        {
            return;
        }
    }

    const auto nodeTriggerSelector = nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>(
        "TriggerSelector");
    const auto nodeTriggerMode = nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("TriggerMode");

    const std::vector<std::string> triggerSelectorDisablePreference = { "ExposureStart", "FrameStart" };

    for (const auto& selectorValue : triggerSelectorDisablePreference)
    {
        if (nodeTriggerSelector->HasEntry(selectorValue))
        {
            nodeTriggerSelector->SetCurrentEntry(selectorValue);
            nodeTriggerMode->SetCurrentEntry("Off");
            break;
        }
    }
}

/*
 * Configure the device for freerun acquisition.
 * Triggers are disabled if loading the default UserSet fails.
 */
void Configure(const std::shared_ptr<peak::core::Device>& device)
{
    // get the remote device node map
    const auto nodeMapRemoteDevice = device->RemoteDevice()->NodeMaps().at(0);

    // general preparations for untriggered continuous image acquisition
    // load the default user set, if available, to reset the device to a defined parameter set
    try
    {
        nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("UserSetSelector")
            ->SetCurrentEntry("Default");
        nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("UserSetLoad")->Execute();
        // wait until the UserSetLoad command has been finished
        nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("UserSetLoad")->WaitUntilDone();
    }
    catch (const std::exception&)
    {
        // UserSet is not available, try to disable ExposureStart or FrameStart trigger manually
        std::cout << "Failed to load UserSet Default. Manual freerun configuration." << std::endl;

        DisableDeviceTrigger(nodeMapRemoteDevice);
    }
}

/*
 * Prepare and start data stream acquisition.
 * Allocates and announces the minimum required buffers and locks critical parameters.
 */
std::shared_ptr<peak::core::DataStream> PrepareAndStartAcquisition(const std::shared_ptr<peak::core::Device>& device)
{
    auto dataStream = device->DataStreams().at(0)->OpenDataStream();

    const auto nodeMapRemoteDevice = device->RemoteDevice()->NodeMaps().at(0);

    // allocate and announce image buffers
    const auto payloadSize = nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("PayloadSize")->Value();
    const auto numBuffersAnnouncedMinRequired = dataStream->NumBuffersAnnouncedMinRequired();
    for (auto bufferCount = std::uint64_t{ 0 }; bufferCount < numBuffersAnnouncedMinRequired; ++bufferCount)
    {
        auto buffer = dataStream->AllocAndAnnounceBuffer(static_cast<size_t>(payloadSize), nullptr);
        dataStream->QueueBuffer(buffer);
    }

    // Lock critical features to prevent them from changing during acquisition
    nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(1);

    // start acquisition
    dataStream->StartAcquisition(peak::core::AcquisitionStartMode::Default);
    nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("AcquisitionStart")->Execute();

    return dataStream;
}

/*
 * Enable remote device events (e.g., ExposureStart) if supported.
 * Used to demonstrate mapping device event timestamps to system timestamps.
 */
std::unique_ptr<peak::core::EventController> EnableRemoteDeviceEventsIfPossible(
    const std::shared_ptr<peak::core::Device>& device)
{
    // Enable ExposureStart events
    try
    {
        const auto nodeMapRemoteDevice = device->RemoteDevice()->NodeMaps().at(0);
        nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("EventSelector")
            ->SetCurrentEntry("ExposureStart");
        nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("EventNotification")->SetCurrentEntry("On");

        return device->EnableEvents(peak::core::EventType::RemoteDevice);
    }
    catch (const std::exception&)
    {
        std::cout << "Could not enable remote device events. Event timestamps will not be shown." << std::endl;
    }

    return {};
}

/*
 * Calculate and print the system timestamp of a remote device event.
 * Maps the device event timestamp to the system time using the last synchronized
 * device-system timestamp pair. A latch is used to ensure a consistent snapshot.
 */
void CalculateAndPrintRemoteDeviceEventSystemTimestamp(const std::shared_ptr<peak::core::Device>& device,
    const std::unique_ptr<peak::core::EventController>& remoteDeviceEventController)
{
    const auto nodeMapRemoteDevice = device->RemoteDevice()->NodeMaps().at(0);

    {
        using namespace std::chrono_literals;
        const auto event = remoteDeviceEventController->WaitForEvent(5'000ms);
        nodeMapRemoteDevice->UpdateEventNodes(event);
    }

    // The following code queries the device timestamp of the event which was attached to the node map. This timestamp
    // is NOT the system timestamp. It's a device specific timestamp which has to be mapped to the system time via the
    // following code in this function.
    const auto eventExposureStartTimestampNode = nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>(
        "EventExposureStartTimestamp");
    const auto eventExposureStartTimestampNs = static_cast<std::uint64_t>(eventExposureStartTimestampNode->Value());

    const auto nodeMapDevice = device->NodeMaps().at(0);

    // System and device timestamp are using a latch mechanism to avoid race conditions in case the automatic update
    // is enabled (SynchronizationTimestampMode == Auto, which is the default setting). This is why we have to execute
    // the SynchronizationTimestampLatch node to get the latest values from the last automatic synchronization.
    const auto timestampLatchNode = nodeMapDevice->FindNode<peak::core::nodes::CommandNode>(
        "SynchronizationTimestampLatch");
    timestampLatchNode->Execute();
    timestampLatchNode->WaitUntilDone();

    const auto systemTimestampNs = static_cast<std::uint64_t>(
        nodeMapDevice->FindNode<peak::core::nodes::IntegerNode>("SynchronizationTimestampSystem")->Value());
    const auto deviceTimestampNs = static_cast<std::uint64_t>(
        nodeMapDevice->FindNode<peak::core::nodes::IntegerNode>("SynchronizationTimestampDevice")->Value());
    const auto eventSystemTimestampNs = systemTimestampNs + (eventExposureStartTimestampNs - deviceTimestampNs);

    std::cout << "--ExposureStartEvent--" << '\n';
    std::cout << "Timestamp [ns]: " << eventExposureStartTimestampNs << '\n';
    std::cout << "System timestamp [time since epoch in ns]: " << eventSystemTimestampNs << '\n';
    PrintStructuredTimestamp(eventSystemTimestampNs, Time::Local);
    PrintStructuredTimestamp(eventSystemTimestampNs, Time::Utc);
}

/*
 * Stop acquisition and release all buffers.
 * Unlocks previously locked parameters.
 */
void StopAcquisition(const std::shared_ptr<peak::core::DataStream>& dataStream)
{
    const auto nodeMapRemoteDevice = dataStream->ParentDevice()->RemoteDevice()->NodeMaps().at(0);

    dataStream->StopAcquisition(peak::core::AcquisitionStopMode::Default);
    nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("AcquisitionStop")->Execute();

    // Unlock parameters after acquisition stop
    nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(0);

    // flush and revoke all buffers
    dataStream->Flush(peak::core::DataStreamFlushMode::DiscardAll);
    for (const auto& buffer : dataStream->AnnouncedBuffers())
    {
        dataStream->RevokeBuffer(buffer);
    }
}

/*
 * Returns true if the device implements all nodes required for system timestamp support.
 */
bool IsSystemTimestampSupported(const std::shared_ptr<peak::core::Device>& device)
{
    const auto nodeMapDevice = device->NodeMaps().at(0);
    const auto& synchronizationTimestampModeNode = nodeMapDevice->FindNode<peak::core::nodes::EnumerationNode>(
        "SynchronizationTimestampMode");
    const auto& synchronizationTimestampSystemNode = nodeMapDevice->FindNode<peak::core::nodes::IntegerNode>(
        "SynchronizationTimestampSystem");
    const auto& synchronizationTimestampDeviceNode = nodeMapDevice->FindNode<peak::core::nodes::IntegerNode>(
        "SynchronizationTimestampDevice");
    const auto& synchronizationTimestampIntervalNode = nodeMapDevice->FindNode<peak::core::nodes::IntegerNode>(
        "SynchronizationTimestampInterval");
    const auto& synchronizationTimestampLatchNode = nodeMapDevice->FindNode<peak::core::nodes::CommandNode>(
        "SynchronizationTimestampLatch");

    return synchronizationTimestampModeNode->IsImplemented() && synchronizationTimestampSystemNode->IsImplemented()
        && synchronizationTimestampDeviceNode->IsImplemented() && synchronizationTimestampIntervalNode->IsImplemented()
        && synchronizationTimestampLatchNode->IsImplemented();
}

/*
 * Print a structured timestamp in human-readable form.
 * Accepts timestamps in nanoseconds since Unix epoch.
 */
void PrintStructuredTimestamp(std::uint64_t timestampTimeSinceEpochNs, Time time)
{
    const auto seconds64 = timestampTimeSinceEpochNs / 1'000'000'000;
    auto seconds = static_cast<std::time_t>(seconds64);

    auto tm = std::tm{};
    switch (time)
    {
    case Time::Local: {
#if defined(_WIN32)
        localtime_s(&tm, &seconds);
#else
        localtime_r(&seconds, &tm);
#endif
        break;
    }
    case Time::Utc: {
#if defined(_WIN32)
        gmtime_s(&tm, &seconds);
#else
        gmtime_r(&seconds, &tm);
#endif
        break;
    }
    }

    const auto nanosecondsAfterSeconds = timestampTimeSinceEpochNs % 1'000'000'000;
    const auto millisecondsAfterSeconds = nanosecondsAfterSeconds / 1'000'000;
    const auto microsecondsAfterMilliseconds = (nanosecondsAfterSeconds / 1'000) % 1'000;
    const auto nanosecondsAfterMicroseconds = nanosecondsAfterSeconds % 1'000;

    std::cout << "Structured timestamp: " << (time == Time::Local ? "[Local]" : "[UTC]") << " "
              << std::put_time(&tm, "%Y-%m-%d %H:%M:%S") << ":" << millisecondsAfterSeconds << ":"
              << microsecondsAfterMilliseconds << ":" << nanosecondsAfterMicroseconds << std::endl;
}
