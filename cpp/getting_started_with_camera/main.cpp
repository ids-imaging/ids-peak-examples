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
 * \brief This application demonstrates how to use the device manager to open a camera
 */

#include <iostream>
#include <memory>
#include <vector>

#include <peak/peak.hpp>
#include <peak_icv/peak_icv.hpp>

int main()
{
    try
    {
        // Initialize libraries
        peak::Library::Initialize();
        peak::icv::library::Init();

        // Initialize DeviceManager and update device list
        auto& deviceManager = peak::DeviceManager::Instance();
        deviceManager.Update();

        // Find the first available camera with control access
        std::shared_ptr<peak::core::DeviceDescriptor> deviceDescriptor = deviceManager.FirstAvailableDevice(
            peak::core::DeviceAccessType::Control);

        if (deviceDescriptor == nullptr)
        {
            std::cerr << "Failed to find any openable camera!" << std::endl;
            peak::Library::Close();
            return -1;
        }

        // Open the device and get the nodemap of the remote device
        auto device = deviceDescriptor->OpenDevice(peak::core::DeviceAccessType::Control);
        auto nodeMapRemoteDevice = device->RemoteDevice()->NodeMaps().at(0);

        // Open the data stream and prepare the buffers
        auto dataStream = device->DataStreams().at(0)->OpenDataStream();

        // Get the required payload size. If the data stream does not
        // define it, fall back to the remote device node map.
        auto payloadSizeNode = nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("PayloadSize");
        auto payloadSize = dataStream->DefinesPayloadSize() ? dataStream->PayloadSize() :
                                                              static_cast<size_t>(payloadSizeNode->Value());

        auto bufferCount = dataStream->NumBuffersAnnouncedMinRequired();

        // Allocate buffers and queue them
        dataStream->AddAcquisitionBuffers(payloadSize, bufferCount);

        // Lock transport layer parameters (TLParamsLocked = 1) to
        // prevent irregular access to the remote device during acquisition
        nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(1);

        // Start acquisition on both data stream and device
        dataStream->StartAcquisition();
        nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("AcquisitionStart")->ExecuteAndWait();

        std::cout << "Acquisition started. Capturing 5 ICV images...\n";

        // Acquire 5 images and wrap them as ICV images
        for (int i = 0; i < 5; ++i)
        {
            // Wait for a filled buffer (timeout: 5000 ms)
            peak::core::BufferGuard guard(dataStream->WaitForFinishedBuffer(5'000));

            // Create an ICV image from the buffer
            auto image = peak::icv::Image(guard.Buffer()->ToImageView());

            // The image can now be used for further processing
            std::cout << "Image " << (i + 1) << " captured! "
                      << "ICV dimensions: " << image.GetSize() << " px, "
                      << "PixelFormat: " << image.GetPixelFormat() << ", "
                      << "First pixel value: " << static_cast<int>(*image.At<uint8_t>(0, 0)) << "\n";
        }

        // Stop acquisition
        nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("AcquisitionStop")->ExecuteAndWait();
        dataStream->StopAcquisition(peak::core::AcquisitionStopMode::Default);

        // Unlock transport layer parameters
        nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(0);

        // Release acquisition buffers
        dataStream->FlushAndRevokeAllBuffers();

        std::cout << "Camera closed and resources released successfully.\n";
    }
    catch (const std::exception& e)
    {
        std::cerr << "Error: " << e.what() << std::endl;
    }

    try
    {
        // Close libraries
        peak::icv::library::Exit();
        peak::Library::Close();
    }
    catch (const std::exception& e)
    {
        std::cerr << "Error: " << e.what() << std::endl;
    }

    return 0;
}
