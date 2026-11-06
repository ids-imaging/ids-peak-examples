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

// Standard headers
#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <vector>

#include <peak/peak.hpp>
#include <peak_icv/peak_icv.hpp>

namespace
{
namespace example_config
{
constexpr size_t imageAcquisitionCount = 1;
constexpr size_t offsetMilliMeter = 42;
} // namespace example_config

struct DeviceInfo
{
    std::shared_ptr<peak::core::Device> device{};
    std::shared_ptr<peak::core::NodeMap> nodeMap{};
};

void InitializeLibraries();
void ExitLibraries();
DeviceInfo OpenFirstAvailableNionCamera();
void DeviceResetToDefault(const std::shared_ptr<peak::core::NodeMap>& nodeMap);
float DeviceGetDepthScaleFactor(const std::shared_ptr<peak::core::NodeMap>& nodeMap);
float DeviceGetDepthCoordinateOffset(const std::shared_ptr<peak::core::NodeMap>& nodeMap);
std::shared_ptr<peak::core::DataStream> DeviceStartAcquisition(
    const std::shared_ptr<peak::core::Device>& device, const std::shared_ptr<peak::core::NodeMap>& nodeMap);
void DeviceStopAcquisition(
    const std::shared_ptr<peak::core::NodeMap>& nodeMap, const std::shared_ptr<peak::core::DataStream>& stream);
void WriteDepthMapToFile(const peak::icv::Image& depthMap, size_t i);
} // namespace

int main()
{
    try
    {
        InitializeLibraries();

        auto deviceInfo = OpenFirstAvailableNionCamera();
        auto nodeMap = deviceInfo.nodeMap;
        auto device = deviceInfo.device;

        DeviceResetToDefault(nodeMap);

        const auto scaleFactor = DeviceGetDepthScaleFactor(nodeMap);
        const auto coordinateOffset = DeviceGetDepthCoordinateOffset(nodeMap);

        const auto offsetDn = static_cast<size_t>(std::lround(example_config::offsetMilliMeter / scaleFactor));

        auto stream = DeviceStartAcquisition(device, nodeMap);

        for (size_t i = 0; i < example_config::imageAcquisitionCount; ++i)
        {
            const auto buffer = peak::core::BufferGuard(stream->WaitForFinishedBuffer(5'000));

            if (buffer->IsIncomplete())
            {
                std::cout << "Incomplete buffer " << i << ". Skipping." << std::endl;
                continue;
            }
            if (!buffer->HasNewData())
            {
                std::cout << "Buffer " << i << " has no new data. Skipping." << std::endl;
                continue;
            }

            peak::icv::Image rawDepth(buffer->ToImageView());
            peak::icv::Image depthMap(peak::common::PixelFormat::Coord3D_C32f, rawDepth.GetSize());

            const auto* srcBegin = reinterpret_cast<uint16_t*>(rawDepth.GetData());
            const auto* srcEnd = srcBegin + (rawDepth.GetSizeInBytes() / sizeof(uint16_t));
            auto* dstBegin = reinterpret_cast<float*>(depthMap.GetData());

            std::transform(
                srcBegin, srcEnd, dstBegin, [offsetDn, scaleFactor, coordinateOffset](const uint16_t& value) {
                    static constexpr size_t maximumValidRange = 4'096;
                    const auto shiftedDn = (offsetDn + value) % maximumValidRange;
                    return static_cast<float>(shiftedDn) * scaleFactor + coordinateOffset;
                });

            WriteDepthMapToFile(depthMap, i);
        }

        DeviceStopAcquisition(nodeMap, stream);
    }
    catch (const std::exception& e)
    {
        std::cerr << "Error: " << e.what() << std::endl;
    }

    ExitLibraries();

    return 0;
}

namespace
{
void InitializeLibraries()
{
    peak::Library::Initialize();
    peak::icv::library::Init();
}

void ExitLibraries()
{
    try
    {
        peak::icv::library::Exit();
        peak::Library::Close();
    }
    catch (...)
    {
        std::cerr << "Error: Exception occured while exiting libraries!";
    }
}

DeviceInfo OpenFirstAvailableNionCamera()
{
    auto& deviceManager = peak::DeviceManager::Instance();
    deviceManager.Update();

    const auto devices = deviceManager.FindDevices([](const std::shared_ptr<peak::core::DeviceDescriptor>& dev) {
        std::string modelName = dev->ModelName();
        std::transform(modelName.begin(), modelName.end(), modelName.begin(), [](unsigned char c) {
            return std::tolower(c);
        });

        return modelName.find("nion") != std::string::npos && dev->IsOpenable();
    });

    if (devices.empty())
    {
        throw std::runtime_error("No IDS Nion device found.");
    }

    const auto device = devices.at(0)->OpenDevice(peak::core::DeviceAccessType::Control);
    const auto nodeMap = device->RemoteDevice()->NodeMaps().at(0);

    return { device, nodeMap };
}

void DeviceResetToDefault(const std::shared_ptr<peak::core::NodeMap>& nodeMap)
{
    nodeMap->FindNode<peak::core::nodes::EnumerationNode>("UserSetSelector")->SetCurrentEntry("Default");

    const auto cmd = nodeMap->FindNode<peak::core::nodes::CommandNode>("UserSetLoad");
    cmd->ExecuteAndWait();
}

// Get the scale factor for converting depth values into metric units
float DeviceGetDepthScaleFactor(const std::shared_ptr<peak::core::NodeMap>& nodeMap)
{
    return static_cast<float>(nodeMap->FindNode<peak::core::nodes::FloatNode>("Scan3dCoordinateScale")->Value());
}

float DeviceGetDepthCoordinateOffset(const std::shared_ptr<peak::core::NodeMap>& nodeMap)
{
    return static_cast<float>(nodeMap->FindNode<peak::core::nodes::FloatNode>("Scan3dCoordinateOffset")->Value());
}

std::shared_ptr<peak::core::DataStream> DeviceStartAcquisition(
    const std::shared_ptr<peak::core::Device>& device, const std::shared_ptr<peak::core::NodeMap>& nodeMap)
{
    nodeMap->FindNode<peak::core::nodes::EnumerationNode>("ImageComponentSelector")->SetCurrentEntry("Intensity");
    nodeMap->FindNode<peak::core::nodes::BooleanNode>("ImageComponentEnable")->SetValue(false);

    nodeMap->FindNode<peak::core::nodes::EnumerationNode>("ImageComponentSelector")->SetCurrentEntry("Confidence");
    nodeMap->FindNode<peak::core::nodes::BooleanNode>("ImageComponentEnable")->SetValue(false);

    auto stream = device->DataStreams().front()->OpenDataStream();

    nodeMap->FindNode<peak::core::nodes::EnumerationNode>("AcquisitionMode")->SetCurrentEntry("Continuous");

    const auto payloadSize = nodeMap->FindNode<peak::core::nodes::IntegerNode>("PayloadSize")->Value();

    stream->AddAcquisitionBuffers(static_cast<size_t>(payloadSize), stream->NumBuffersAnnouncedMinRequired());

    nodeMap->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(1);

    stream->StartAcquisition();

    const auto cmd = nodeMap->FindNode<peak::core::nodes::CommandNode>("AcquisitionStart");
    cmd->ExecuteAndWait();

    return stream;
}

void DeviceStopAcquisition(
    const std::shared_ptr<peak::core::NodeMap>& nodeMap, const std::shared_ptr<peak::core::DataStream>& stream)
{
    const auto cmd = nodeMap->FindNode<peak::core::nodes::CommandNode>("AcquisitionStop");
    cmd->ExecuteAndWait();

    stream->StopAcquisition();
    nodeMap->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(0);

    stream->FlushAndRevokeAllBuffers();
}

void WriteDepthMapToFile(const peak::icv::Image& depthMap, size_t i)
{
    const peak::icv::ImageWriter imageWriter;

    const auto filePath = "depth_map_" + std::to_string(i) + ".tiff";
    imageWriter.Write(filePath, depthMap);
    std::cout << "Depth map written to: " << filePath << std::endl;
}
} // namespace
