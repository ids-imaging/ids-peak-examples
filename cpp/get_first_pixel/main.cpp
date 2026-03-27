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

/*!
 * \brief This example demonstrates how to acquire an image and print the value of the first pixel.
 */
#include <peak/peak.hpp>

#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>

namespace
{
class LibraryGuard
{
public:
    LibraryGuard()
    {
        peak::Library::Initialize();
    }

    ~LibraryGuard()
    {
        try
        {
            peak::Library::Close();
        }
        catch (const std::exception& e)
        {
            std::cout << "EXCEPTION: " << e.what() << "\n";
        }
    }
};

void WaitForEnterPressed();
std::shared_ptr<peak::core::Device> ChooseDevice();
std::shared_ptr<peak::core::DataStream> StartAcquisition(const std::shared_ptr<peak::core::Device>& device);
void StopAcquisition(const std::shared_ptr<peak::core::DataStream>& dataStream);
} // namespace

int main()
{
    try
    {
        const LibraryGuard libraryGuard;

        auto device = ChooseDevice();
        auto dataStream = StartAcquisition(device);

        constexpr auto numBuffersToAcquire = 10;
        for (std::size_t i = 0; i < numBuffersToAcquire; ++i)
        {
            using namespace std::chrono_literals;
            auto buffer = dataStream->WaitForFinishedBuffer(peak::core::Timeout(5s));
            auto imageView = buffer->ToImageView();

            std::cout << std::to_string(*imageView.GetData()) << " ";

            dataStream->QueueBuffer(buffer);
        }
        std::cout << "\n";

        StopAcquisition(dataStream);

        WaitForEnterPressed();

        return EXIT_SUCCESS;
    }
    catch (const std::exception& e)
    {
        std::cout << "EXCEPTION: " << e.what() << "\n";
        return EXIT_FAILURE;
    }
}

namespace
{

void WaitForEnterPressed()
{
    std::cout << "\nPress Enter to exit...\n";
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
    std::cin.get();
}

std::shared_ptr<peak::core::Device> ChooseDevice()
{
    // create a camera manager object
    auto& deviceManager = peak::DeviceManager::Instance();

    // update the camera manager
    deviceManager.Update();

    if (deviceManager.Devices().empty())
    {
        throw std::runtime_error("No camera found.");
    }

    // list all available devices
    std::uint64_t i = 0;
    std::cout << "Devices available: \n";
    for (const auto& deviceDescriptor : deviceManager.Devices())
    {
        std::cout << i << ": " << deviceDescriptor->ModelName() << " ("
                  << deviceDescriptor->ParentInterface()->DisplayName() << "; "
                  << deviceDescriptor->ParentInterface()->ParentSystem()->DisplayName() << " v."
                  << deviceDescriptor->ParentInterface()->ParentSystem()->Version() << ")\n";
        ++i;
    }

    // select a camera to open
    size_t selectedDevice = 0;

    while (true)
    {
        std::cout << "\nSelect camera index to open [0 - " << deviceManager.Devices().size() - 1 << "]: ";
        std::cin >> selectedDevice;

        if (std::cin.fail() || selectedDevice >= deviceManager.Devices().size())
        {
            std::cout << "Invalid input!\n";
            std::cin.clear();
            std::cin.ignore(1'000, '\n');
            continue;
        }
        break;
    }

    // open the selected camera
    return deviceManager.Devices().at(selectedDevice)->OpenDevice(peak::core::DeviceAccessType::Control);
}

std::shared_ptr<peak::core::DataStream> StartAcquisition(const std::shared_ptr<peak::core::Device>& device)
{
    // get the remote device node map
    auto nodeMapRemoteDevice = device->RemoteDevice()->NodeMaps().at(0);

    // Open standard data stream
    auto dataStream = device->DataStreams().at(0)->OpenDataStream();

    // load the default user set to reset the device
    nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("UserSetSelector")->SetCurrentEntry("Default");
    auto userSetLoadNode = nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("UserSetLoad");
    userSetLoadNode->Execute();
    userSetLoadNode->WaitUntilDone();

    // allocate and announce image buffers
    auto payloadSize = dataStream->DefinesPayloadSize() ?
        dataStream->PayloadSize() :
        static_cast<std::size_t>(nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("PayloadSize")->Value());
    const auto numBuffersMinRequired = dataStream->NumBuffersAnnouncedMinRequired();
    for (std::uint64_t i = 0; i < numBuffersMinRequired; ++i)
    {
        auto buffer = dataStream->AllocAndAnnounceBuffer(payloadSize, nullptr);
        dataStream->QueueBuffer(buffer);
    }

    // Lock critical features to prevent them from changing during acquisition
    nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(1);

    // start acquisition
    dataStream->StartAcquisition(peak::core::AcquisitionStartMode::Default);
    auto acquisitionStartNode = nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("AcquisitionStart");
    acquisitionStartNode->Execute();
    acquisitionStartNode->WaitUntilDone();

    return dataStream;
}

void StopAcquisition(const std::shared_ptr<peak::core::DataStream>& dataStream)
{
    // stop acquisition of camera
    dataStream->StopAcquisition(peak::core::AcquisitionStopMode::Default);

    auto device = dataStream->ParentDevice();
    auto nodeMapRemoteDevice = device->RemoteDevice()->NodeMaps().at(0);

    auto acquisitionStopNode = nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("AcquisitionStop");
    acquisitionStopNode->Execute();
    acquisitionStopNode->WaitUntilDone();

    // Unlock parameters after acquisition stop
    nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(0);

    // flush and revoke all buffers
    dataStream->Flush(peak::core::DataStreamFlushMode::DiscardAll);
    for (const auto& buffer : dataStream->AnnouncedBuffers())
    {
        dataStream->RevokeBuffer(buffer);
    }
}

} // namespace
