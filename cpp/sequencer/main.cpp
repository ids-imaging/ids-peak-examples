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
 * \brief This example demonstrates how to use the sequencer feature of a camera.
 */

#include <peak/peak.hpp>
#include <peak_common/peak_common.hpp>
#include <peak_icv/peak_icv.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

namespace
{
constexpr std::size_t sequenceLength = 4;

std::shared_ptr<peak::core::Device> OpenFirstAvailableSequencerDevice();
void StopAcquisition(const std::shared_ptr<peak::core::DataStream>& dataStream);
std::vector<double> CreateFeatureValues(const std::shared_ptr<peak::core::nodes::FloatNode>& featureNode);
void ResetToDefault(const std::shared_ptr<peak::core::Device>& device);
} // namespace

int main()
{
    try
    {
        peak::Library::Initialize();
        peak::icv::library::Init();

        const auto device = OpenFirstAvailableSequencerDevice();
        ResetToDefault(device);

        const auto nodeMapRemoteDevice = device->RemoteDevice()->NodeMaps().at(0);

        {
            // configure counter, sequencer and trigger
            if (nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("SequencerMode")
                    ->CurrentEntry()
                    ->SymbolicValue()
                != "Off")
            {
                nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("SequencerMode")
                    ->SetCurrentEntry("Off");
            }
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("SequencerConfigurationMode")
                ->SetCurrentEntry("On");

            const auto sequencerFeatureSelector = nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>(
                "SequencerFeatureSelector");
            const auto sequencerFeatureEnable = nodeMapRemoteDevice->FindNode<peak::core::nodes::BooleanNode>(
                "SequencerFeatureEnable");
            sequencerFeatureSelector->SetCurrentEntry("ExposureTime");
            if (!sequencerFeatureEnable->Value())
            {
                sequencerFeatureEnable->SetValue(true);
            }
            sequencerFeatureSelector->SetCurrentEntry("Gain");
            if (!sequencerFeatureEnable->Value())
            {
                sequencerFeatureEnable->SetValue(true);
            }

            const auto exposureValues = CreateFeatureValues(
                nodeMapRemoteDevice->FindNode<peak::core::nodes::FloatNode>("ExposureTime"));
            sequencerFeatureSelector->SetCurrentEntry("Gain");
            const auto gainValues = CreateFeatureValues(
                nodeMapRemoteDevice->FindNode<peak::core::nodes::FloatNode>("Gain"));

            for (std::size_t i = 0; i < sequenceLength; ++i)
            {
                nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("SequencerSetSelector")
                    ->SetValue(static_cast<int64_t>(i));
                nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("SequencerSetNext")
                    ->SetValue(static_cast<int64_t>((i + 1) % sequenceLength));
                nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("SequencerTriggerSource")
                    ->SetCurrentEntry("ExposureStart");
                nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("SequencerTriggerActivation")
                    ->SetCurrentEntry("RisingEdge");

                sequencerFeatureSelector->SetCurrentEntry("ExposureTime");
                nodeMapRemoteDevice->FindNode<peak::core::nodes::FloatNode>("ExposureTime")
                    ->SetValue(exposureValues.at(i));

                sequencerFeatureSelector->SetCurrentEntry("Gain");
                nodeMapRemoteDevice->FindNode<peak::core::nodes::FloatNode>("Gain")->SetValue(gainValues.at(i));

                nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("SequencerSetSave")->ExecuteAndWait();

                std::cout << "Sequencer set " << i << ": ExposureTime = " << exposureValues.at(i) << " us\n";
                std::cout << "Sequencer set " << i << ": Gain = " << gainValues.at(i) << '\n';
            }

            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("SequencerConfigurationMode")
                ->SetCurrentEntry("Off");

            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("CounterSelector")
                ->SetCurrentEntry("Counter0");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("CounterEventSource")
                ->SetCurrentEntry("ExposureStart");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("CounterDuration")
                ->SetValue(static_cast<int64_t>(sequenceLength));

            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("TriggerSelector")
                ->SetCurrentEntry("ExposureStart");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("TriggerMode")->SetCurrentEntry("On");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("TriggerSource")
                ->SetCurrentEntry("Counter0Active");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("TriggerActivation")
                ->SetCurrentEntry("LevelHigh");

            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("SequencerMode")->SetCurrentEntry("On");
        }

        std::shared_ptr<peak::core::DataStream> dataStream;
        {
            // configure and start acquisition
            dataStream = device->DataStreams().at(0)->OpenDataStream();
            const auto payloadSize = dataStream->DefinesPayloadSize() ?
                dataStream->PayloadSize() :
                static_cast<std::size_t>(
                    nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("PayloadSize")->Value());
            const auto numBuffersMinRequired = dataStream->NumBuffersAnnouncedMinRequired();
            dataStream->AddAcquisitionBuffers(payloadSize, numBuffersMinRequired);
            nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(1);
            dataStream->StartAcquisition(peak::core::AcquisitionStartMode::Default);
            nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("AcquisitionStart")->ExecuteAndWait();
        }

        {
            // start the sequence
            nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("CounterSelector")
                ->SetCurrentEntry("Counter0");
            nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("CounterReset")->ExecuteAndWait();
        }

        for (std::size_t i = 0; i < sequenceLength; ++i)
        {
            using namespace std::chrono_literals;

            peak::core::BufferGuard buffer{ dataStream->WaitForFinishedBuffer(peak::core::Timeout(5s)) };
            const peak::icv::Image image{ buffer->ToImageView() };

            try
            {
                const auto fileName = "sequencer_image_" + std::to_string(i + 1) + ".png";

                constexpr peak::icv::ImageWriter imageWriter;
                imageWriter.Write(fileName, image);
                std::cout << "Saved " << fileName << '\n';
            }
            catch (const std::exception& e)
            {
                std::cout << "Failed to save image " << i << ": " << e.what() << '\n';
            }
        }

        StopAcquisition(dataStream);
    }
    catch (const std::exception& e)
    {
        std::cout << "EXCEPTION: " << e.what() << "\n";
        return 1;
    }

    try
    {
        peak::icv::library::Exit();
        peak::Library::Close();
    }
    catch (const std::exception& e)
    {
        std::cout << "EXCEPTION: " << e.what() << "\n";
        return 1;
    }

    return 0;
}

namespace
{

std::shared_ptr<peak::core::Device> OpenFirstAvailableSequencerDevice()
{
    auto& deviceManager = peak::DeviceManager::Instance();

    deviceManager.Update();

    const auto devices = deviceManager.AvailableDevices(peak::core::DeviceAccessType::Control);
    for (const auto& deviceDescriptor : devices)
    {
        constexpr std::array<const char*, 20> requiredSampleNodes{ "SequencerMode", "SequencerConfigurationMode",
            "SequencerFeatureSelector", "SequencerFeatureEnable", "SequencerSetSelector", "SequencerPathSelector",
            "SequencerSetNext", "SequencerSetSave", "SequencerTriggerSource", "SequencerTriggerActivation",
            "ExposureTime", "Gain", "CounterSelector", "CounterEventSource", "CounterDuration", "CounterReset",
            "TriggerSelector", "TriggerMode", "TriggerSource", "TriggerActivation" };
        const auto device = deviceDescriptor->OpenDevice(peak::core::DeviceAccessType::Control);
        if (std::all_of(requiredSampleNodes.cbegin(), requiredSampleNodes.cend(), [&device](const auto* nodeName) {
                return device->RemoteDevice()->NodeMaps().at(0)->HasNode(nodeName);
            }))
        {
            return device;
        }
    }

    throw std::runtime_error("No camera with the required sequencer nodes is available.");
}

void ResetToDefault(const std::shared_ptr<peak::core::Device>& device)
{
    const auto nodeMapRemoteDevice = device->RemoteDevice()->NodeMaps().at(0);
    nodeMapRemoteDevice->FindNode<peak::core::nodes::EnumerationNode>("UserSetSelector")->SetCurrentEntry("Default");
    const auto userSetLoadNode = nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("UserSetLoad");
    userSetLoadNode->ExecuteAndWait();
}

void StopAcquisition(const std::shared_ptr<peak::core::DataStream>& dataStream)
{
    // stop acquisition of camera
    auto device = dataStream->ParentDevice();
    auto nodeMapRemoteDevice = device->RemoteDevice()->NodeMaps().at(0);

    auto acquisitionStopNode = nodeMapRemoteDevice->FindNode<peak::core::nodes::CommandNode>("AcquisitionStop");
    acquisitionStopNode->Execute();
    acquisitionStopNode->WaitUntilDone();

    dataStream->StopAcquisition(peak::core::AcquisitionStopMode::Default);

    // Unlock parameters after acquisition stop
    nodeMapRemoteDevice->FindNode<peak::core::nodes::IntegerNode>("TLParamsLocked")->SetValue(0);

    // flush and revoke all buffers
    dataStream->Flush(peak::core::DataStreamFlushMode::DiscardAll);
    for (const auto& buffer : dataStream->AnnouncedBuffers())
    {
        dataStream->RevokeBuffer(buffer);
    }
}

std::vector<double> CreateFeatureValues(const std::shared_ptr<peak::core::nodes::FloatNode>& featureNode)
{
    const auto minimum = featureNode->Minimum();
    const auto maximum = featureNode->Maximum();

    return { std::max(minimum, maximum / 4.0), std::max(minimum, maximum / 2.0), std::max(minimum, maximum * 3.0 / 4.0),
        maximum };
}

} // namespace
