/*
 * Copyright(C) 2025, IDS Imaging Development Systems GmbH.
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
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

#include <peak/peak.hpp>
#include <peak_icv/peak_icv.hpp>

namespace
{
    // ---------------------------------------------------------------------------------------------------------------------
    // CONFIGURATION
    // ---------------------------------------------------------------------------------------------------------------------

    // Enable filtering of depth values based on the camera confidence image
    constexpr bool filterDepthMapByConfidenceEnabled = true;

    // Pixels with confidence values below this threshold are marked as invalid. The Range is 0 to 4095.
    constexpr int32_t confidenceThreshold = 100;

    // Camera exposure time in microseconds
    constexpr float exposureTimeUs = 1000.0F;

    // Enable filtering of depth values based on the Z distance
    constexpr bool filterDistanceEnabled = true;

    // Valid Z distance interval in millimeters
    constexpr peak::common::IntervalF filterDistanceIntervalMm{100.0F, 1000.0F};

    // Number of images acquired in this example
    constexpr size_t imageAcquisitionCount = 10;

    // ---------------------------------------------------------------------------------------------------------------------
    // UTILITIES
    // ---------------------------------------------------------------------------------------------------------------------

    struct DeviceInfo
    {
        std::shared_ptr<peak::core::Device> device{};
        std::shared_ptr<peak::core::NodeMap> nodeMap{};
    };

    // Structure holding the required multipart buffer parts
    struct MultipartBuffer
    {
        std::shared_ptr<peak::core::BufferPart> depthMap{};
        std::shared_ptr<peak::core::BufferPart> intensity{};
    };

    // ---------------------------------------------------------------------------------------------------------------------
    // DECLARATIONS
    // ---------------------------------------------------------------------------------------------------------------------

    void InitializeLibraries();

    void ExitLibraries();

    DeviceInfo OpenFirstConnectedDevice();

    void DeviceResetToDefault(const std::shared_ptr<peak::core::NodeMap>& nodeMap);

    void DeviceSetConfidenceThreshold(const std::shared_ptr<peak::core::NodeMap>& nodeMap, int32_t threshold);

    void DeviceSetExposureTime(const std::shared_ptr<peak::core::NodeMap>& nodeMap);

    peak::icv::CalibrationParameters DeviceReadCalibrationParameters(
        const std::shared_ptr<peak::core::NodeMap>& nodeMap);

    float DeviceGetDepthMinimumValidValue(const std::shared_ptr<peak::core::NodeMap>& nodeMap);

    float DeviceGetDepthMaximumValidValue(const std::shared_ptr<peak::core::NodeMap>& nodeMap);

    float DeviceGetDepthScaleFactor(const std::shared_ptr<peak::core::NodeMap>& nodeMap);

    peak::common::Metadata DeviceGetImageMetadata(const std::shared_ptr<peak::core::NodeMap>& nodeMap);

    std::shared_ptr<peak::core::DataStream> DeviceStartAcquisition(
        const std::shared_ptr<peak::core::Device>& device, const std::shared_ptr<peak::core::NodeMap>& nodeMap);

    MultipartBuffer ExtractBufferParts(const std::shared_ptr<peak::core::Buffer>& buffer);

    void DeviceStopAcquisition(
        const std::shared_ptr<peak::core::NodeMap>& nodeMap, const std::shared_ptr<peak::core::DataStream>& stream);

    std::string GetOutputFilePath();

    void WriteDepthMapToFile(const peak::icv::Image& depthMap, size_t i);

    void WriteIntensityToFile(const peak::icv::Image& intensity, size_t i);

    void WritePointCloudToFile(const peak::icv::PointCloudXYZI& pointCloud, size_t i);
} // namespace

// ---------------------------------------------------------------------------------------------------------------------
// MAIN
// ---------------------------------------------------------------------------------------------------------------------

int main()
{
    try
    {
        InitializeLibraries();

        auto deviceInfo = OpenFirstConnectedDevice();
        auto nodeMap = deviceInfo.nodeMap;
        auto device = deviceInfo.device;

        DeviceResetToDefault(nodeMap);

        if (filterDepthMapByConfidenceEnabled)
        {
            DeviceSetConfidenceThreshold(nodeMap, confidenceThreshold);
        }

        DeviceSetExposureTime(nodeMap);

        const auto calibration = DeviceReadCalibrationParameters(nodeMap);
        const auto minimumValidValue = DeviceGetDepthMinimumValidValue(nodeMap);
        const auto maximumValidValue = DeviceGetDepthMaximumValidValue(nodeMap);
        const auto scaleFactor = DeviceGetDepthScaleFactor(nodeMap);
        const auto metadata = DeviceGetImageMetadata(nodeMap);

        // Undistortion object initialized with factory calibration data
        peak::icv::Undistortion undistortion(calibration);

        // Applies nearest-neighbor interpolation
        // during undistortion to strictly maintain measured physical geometry
        // and avoid calculating false, floating depth values.
        undistortion.SetInterpolation(peak::icv::Interpolation::NearestNeighbor);

        auto stream = DeviceStartAcquisition(device, nodeMap);

        for (size_t i = 0; i < imageAcquisitionCount; ++i)
        {
            auto buffer = stream->WaitForFinishedBuffer(PEAK_INFINITE_TIMEOUT);

            if (buffer->IsIncomplete())
            {
                std::cout << "Incomplete buffer " << i << ". Skipping." << std::endl;
                stream->QueueBuffer(buffer);
                continue;
            }
            if (!buffer->HasNewData())
            {
                std::cout << "Buffer " << i << " has no new data. Skipping." << std::endl;
                stream->QueueBuffer(buffer);
                continue;
            }

            if (!buffer->HasParts())
            {
                throw std::runtime_error("Buffer has no parts. Aborting.");
            }

            auto parts = ExtractBufferParts(buffer);

            // ---------------------------------------------------------------------------------------------------------
            // Depth map processing
            // ---------------------------------------------------------------------------------------------------------

            // Create image from raw depth buffer and attach metadata
            peak::icv::Image rawDepth(parts.depthMap->ToImageView());
            rawDepth.SetMetadata(metadata);

            // Convert depth values to floating-point metric coordinates
            auto depth = rawDepth.ConvertPixelFormatWithFactor(peak::common::PixelFormat::Coord3D_C32f, scaleFactor);

            // Remove invalid depth pixels and get region of only valid pixels
            peak::icv::ThresholdF validPixelThreshold{minimumValidValue, maximumValidValue};

            auto validPixelsRegion = validPixelThreshold.Process(depth);

            depth.SetRegion(validPixelsRegion);

            // Undistort the depth map
            auto undistortedDepth = undistortion.Process(depth);

            // Optional distance-based filtering
            if (filterDistanceEnabled)
            {
                peak::icv::ThresholdF distanceFilter(filterDistanceIntervalMm);
                undistortedDepth.SetRegion(distanceFilter.Process(undistortedDepth));
            }

            WriteDepthMapToFile(undistortedDepth, i);

            // ---------------------------------------------------------------------------------------------------------
            // Intensity image processing
            // ---------------------------------------------------------------------------------------------------------

            peak::icv::Image intensity(parts.intensity->ToImageView());
            intensity.SetMetadata(metadata);

            auto undistortedIntensity = undistortion.Process(intensity);
            WriteIntensityToFile(undistortedIntensity, i);

            // Queue buffer that it can be reused. This can be done after the buffer data is no longer used.
            stream->QueueBuffer(buffer);

            // ---------------------------------------------------------------------------------------------------------
            // Point cloud generation
            // ---------------------------------------------------------------------------------------------------------

            peak::icv::PointCloudXYZI pointCloud(undistortedDepth, undistortedIntensity);

            // Applies the extrinsic calibration parameters from the factory calibration
            // to shift the coordinate system's origin
            // from the optical center directly to the front housing of the Nion camera.
            // Alternatively, a workspace calibration can be performed
            // to define the origin at any desired location within the scene.
            auto transformedPointCloud = pointCloud.TransformToWorkspace(calibration.GetExtrinsicParameters());

            WritePointCloudToFile(transformedPointCloud, i);
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
    // ---------------------------------------------------------------------------------------------------------------------
    // PEAK LIBRARY LIFECYCLE
    // ---------------------------------------------------------------------------------------------------------------------

    // Initialize peak core and peak ICV libraries
    void InitializeLibraries()
    {
        peak::Library::Initialize();
        peak::icv::library::Init();
    }

    // Shutdown peak libraries
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

    // ---------------------------------------------------------------------------------------------------------------------
    // DEVICE UTILITIES
    // ---------------------------------------------------------------------------------------------------------------------

    // Open the first connected IDS Nion device
    DeviceInfo OpenFirstConnectedDevice()
    {
        auto& deviceManager = peak::DeviceManager::Instance();
        deviceManager.Update();

        auto devices = deviceManager.Devices();

        const auto it = std::find_if(
            devices.cbegin(), devices.cend(), [](const std::shared_ptr<peak::core::DeviceDescriptor>& dev)
            {
                std::string modelName = dev->ModelName();
                std::transform(modelName.begin(), modelName.end(), modelName.begin(), [](unsigned char c)
                {
                    return std::tolower(c);
                });

                return modelName.find("nion") != std::string::npos && dev->IsOpenable();
            });

        if (it == devices.end())
        {
            throw std::runtime_error("No IDS Nion device found.");
        }

        const auto device = (*it)->OpenDevice(peak::core::DeviceAccessType::Control);
        const auto nodeMap = device->RemoteDevice()->NodeMaps().at(0);

        return {device, nodeMap};
    }

    void DeviceResetToDefault(const std::shared_ptr<peak::core::NodeMap>& nodeMap)
    {
        nodeMap->FindNode<peak::core::nodes::EnumerationNode>("UserSetSelector")->SetCurrentEntry("Default");

        const auto cmd = nodeMap->FindNode<peak::core::nodes::CommandNode>("UserSetLoad");
        cmd->Execute();
        cmd->WaitUntilDone();
    }

    void DeviceSetConfidenceThreshold(const std::shared_ptr<peak::core::NodeMap>& nodeMap, int32_t threshold)
    {
        // Sets the gray value of all pixels in the Range component whose corresponding value in the Confidence
        // component is below the set threshold to Scan3dInvalidDataValue.
        nodeMap->FindNode<peak::core::nodes::IntegerNode>("Scan3dRangeConfidenceThreshold")->SetValue(threshold);
    }

    void DeviceSetExposureTime(const std::shared_ptr<peak::core::NodeMap>& nodeMap)
    {
        nodeMap->FindNode<peak::core::nodes::FloatNode>("ExposureTime")->SetValue(exposureTimeUs);
    }

    peak::icv::CalibrationParameters DeviceReadCalibrationParameters(
        const std::shared_ptr<peak::core::NodeMap>& nodeMap)
    {
        const peak::core::file::FileAdapter adapter(nodeMap, "LensCalibrationData");

        if ((int)adapter.Size() <= 0)
        {
            throw std::runtime_error("No factory calibration data available.");
        }

        return peak::icv::CalibrationParameters(adapter.Read(adapter.Size()));
    }

    float DeviceGetDepthMinimumValidValue(const std::shared_ptr<peak::core::NodeMap>& nodeMap)
    {
        return static_cast<float>(nodeMap->FindNode<peak::core::nodes::FloatNode>("Scan3dAxisMin")->Value());
    }

    float DeviceGetDepthMaximumValidValue(const std::shared_ptr<peak::core::NodeMap>& nodeMap)
    {
        return static_cast<float>(nodeMap->FindNode<peak::core::nodes::FloatNode>("Scan3dAxisMax")->Value());
    }

    // Get the scale factor for converting depth values into metric units
    float DeviceGetDepthScaleFactor(const std::shared_ptr<peak::core::NodeMap>& nodeMap)
    {
        return static_cast<float>(nodeMap->FindNode<peak::core::nodes::FloatNode>("Scan3dCoordinateScale")->Value());
    }

    // Create a metadata object containing binning and ROI information
    // The metadata is required for correct undistortion of images.
    peak::common::Metadata DeviceGetImageMetadata(const std::shared_ptr<peak::core::NodeMap>& nodeMap)
    {
        peak::common::Metadata metadata;

        metadata.SetValueByKey<peak::common::MetadataKey::BinningHorizontal>(
            nodeMap->FindNode<peak::core::nodes::IntegerNode>("BinningHorizontal")->Value());
        metadata.SetValueByKey<peak::common::MetadataKey::BinningVertical>(
            nodeMap->FindNode<peak::core::nodes::IntegerNode>("BinningVertical")->Value());

        peak::common::RectangleU roi{
            static_cast<uint32_t>(
                nodeMap->FindNode<peak::core::nodes::IntegerNode>("OffsetX")->Value()),
            static_cast<uint32_t>(nodeMap->FindNode<peak::core::nodes::IntegerNode>("OffsetY")->Value()),
            static_cast<uint32_t>(nodeMap->FindNode<peak::core::nodes::IntegerNode>("Width")->Value()),
            static_cast<uint32_t>(nodeMap->FindNode<peak::core::nodes::IntegerNode>("Height")->Value())
        };

        metadata.SetValueByKey<peak::common::MetadataKey::Roi>(roi);
        return metadata;
    }

    // ---------------------------------------------------------------------------------------------------------------------
    // ACQUISITION
    // ---------------------------------------------------------------------------------------------------------------------

    // Start image acquisition and prepare the data stream
    std::shared_ptr<peak::core::DataStream> DeviceStartAcquisition(
        const std::shared_ptr<peak::core::Device>& device, const std::shared_ptr<peak::core::NodeMap>& nodeMap)
    {
        auto stream = device->DataStreams().front()->OpenDataStream();

        nodeMap->FindNode<peak::core::nodes::EnumerationNode>("AcquisitionMode")->SetCurrentEntry("Continuous");

        const auto payloadSize = nodeMap->FindNode<peak::core::nodes::IntegerNode>("PayloadSize")->Value();

        for (size_t i = 0; i < stream->NumBuffersAnnouncedMinRequired(); ++i)
        {
            stream->QueueBuffer(stream->AllocAndAnnounceBuffer(static_cast<size_t>(payloadSize), nullptr));
        }

        nodeMap->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(1);

        stream->StartAcquisition();

        const auto cmd = nodeMap->FindNode<peak::core::nodes::CommandNode>("AcquisitionStart");
        cmd->Execute();
        cmd->WaitUntilDone();

        return stream;
    }

    // Extract depth and intensity images from a multipart buffer
    MultipartBuffer ExtractBufferParts(const std::shared_ptr<peak::core::Buffer>& buffer)
    {
        const auto& parts = buffer->Parts();

        auto getPart = [&](peak::core::BufferPartType type)
        {
            const auto it = std::find_if(parts.begin(), parts.end(), [&](const auto& p)
            {
                return p->Type() == type;
            });

            if (it == parts.end())
            {
                throw std::runtime_error("Missing buffer part: " + ToString(type));
            }

            return *it;
        };

        return {getPart(peak::core::BufferPartType::Image3D), getPart(peak::core::BufferPartType::Image2D)};
    }

    // Stop acquisition and release buffers
    void DeviceStopAcquisition(
        const std::shared_ptr<peak::core::NodeMap>& nodeMap, const std::shared_ptr<peak::core::DataStream>& stream)
    {
        const auto cmd = nodeMap->FindNode<peak::core::nodes::CommandNode>("AcquisitionStop");
        cmd->Execute();
        cmd->WaitUntilDone();

        stream->StopAcquisition();
        nodeMap->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(0);

        stream->Flush(peak::core::DataStreamFlushMode::DiscardAll);

        for (auto& b : stream->AnnouncedBuffers())
        {
            stream->RevokeBuffer(b);
        }
    }

    // ---------------------------------------------------------------------------------------------------------------------
    // FILE OUTPUT
    // ---------------------------------------------------------------------------------------------------------------------

    // Get platform-dependent output directory
    std::string GetOutputFilePath()
    {
#ifdef __linux__
        return "/tmp/";
#elif _WIN32
        return "C:/Users/Public/Pictures/";
#else
#    error Platform not supported
#endif
    }

    void WriteDepthMapToFile(const peak::icv::Image& depthMap, size_t i)
    {
        const peak::icv::ImageWriter imageWriter;

        // When written to file the set region is ignored and
        // all pixels are displayed if you want to change this
        // you have to paint the unused pixels with the Painter class
        const auto undistortedDepthMapFilePath = GetOutputFilePath() + "undistorted_depth_map_" + std::to_string(i)
            + ".tiff";
        imageWriter.Write(undistortedDepthMapFilePath, depthMap);
        std::cout << "Undistorted depth map written to: " << undistortedDepthMapFilePath << std::endl;
    }

    void WriteIntensityToFile(const peak::icv::Image& intensity, size_t i)
    {
        const peak::icv::ImageWriter imageWriter;

        const auto undistortedIntensityImageFilePath = GetOutputFilePath() + "undistorted_intensity_image_"
            + std::to_string(i) + ".png";
        imageWriter.Write(undistortedIntensityImageFilePath, intensity);
        std::cout << "Undistorted intensity image written to: " << undistortedIntensityImageFilePath << std::endl;
    }

    void WritePointCloudToFile(const peak::icv::PointCloudXYZI& pointCloud, size_t i)
    {
        const peak::icv::PointCloudWriter pointCloudWriter;

        const auto pointCloudFilePath = GetOutputFilePath() + "point_cloud_xyzi_" + std::to_string(i) + ".ply";

        pointCloudWriter.Write(pointCloudFilePath, pointCloud);
        std::cout << "Point cloud written to: " << pointCloudFilePath << std::endl;
    }
} // namespace
