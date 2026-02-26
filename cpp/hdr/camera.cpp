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

#include "camera.hpp"

#include <algorithm>
#include <iostream>
#include <stdexcept>

namespace hdr
{
namespace
{
constexpr std::array<const char*, 3> frameStartTriggerEntries = {
    "ExposureStart",
    "FrameStart",
    "ReadOutStart",
};

std::string UserSetToString(UserSet userSet)
{
    switch (userSet)
    {
    case UserSet::Default:
        return "Default";
    case UserSet::HighSpeed:
        return "HighSpeed";
    case UserSet::Linescan:
        return "Linescan";
    case UserSet::LinescanHighSpeed:
        return "LinescanHighSpeed";
    case UserSet::LongExposure:
        return "LongExposure";
    case UserSet::UserSet0:
        return "UserSet0";
    case UserSet::UserSet1:
        return "UserSet1";
    case UserSet::QuadHdr:
        return "QuadHDR";
    case UserSet::ClearHdr:
        return "ClearHDR";
    }
    throw std::invalid_argument("Unknown UserSet value");
}

std::vector<std::string> GetEnumEntriesAsStrings(
    const std::vector<std::shared_ptr<peak::core::nodes::EnumerationEntryNode>>& entries)
{
    std::vector<std::string> strings;
    strings.resize(entries.size());
    std::transform(entries.begin(), entries.end(), strings.begin(), [](const auto& entry) {
        return entry->SymbolicValue();
    });
    return strings;
}

std::string FindPreferredFrameStartTrigger(const std::vector<std::string>& availableEntries)
{
    for (const auto& trigger : frameStartTriggerEntries)
    {
        if (std::find(availableEntries.cbegin(), availableEntries.cend(), trigger) != availableEntries.cend())
        {
            return trigger;
        }
    }

    throw std::runtime_error("None of the preferred frame start trigger is available.");
}

std::vector<std::string> FindAvailableFrameStartTriggers(const std::vector<std::string>& availableEntries)
{
    std::vector<std::string> availableTriggers;
    for (const auto& trigger : frameStartTriggerEntries)
    {
        if (std::find(availableEntries.cbegin(), availableEntries.cend(), trigger) != availableEntries.cend())
        {
            availableTriggers.emplace_back(trigger);
        }
    }

    return availableTriggers;
}

} // namespace

Camera::Camera(const std::shared_ptr<peak::core::Device>& device)
    : m_device(device)
{
    if (!m_device)
    {
        throw std::runtime_error("Device is null");
    }

    // Open data stream
    if (m_device->DataStreams().empty())
    {
        throw std::runtime_error("No datastreams available");
    }
    const auto dataStreamDescriptor = m_device->DataStreams().at(0);
    try
    {
        m_dataStream = dataStreamDescriptor->OpenedDataStream();
    }
    catch (const peak::core::Exception& /*unused*/)
    {
        m_dataStream = dataStreamDescriptor->OpenDataStream();
    }

    // Initialize NodeMaps
    if (!m_device->RemoteDevice()->NodeMaps().empty())
    {
        m_nodeMaps[NodeMapType::RemoteDevice] = m_device->RemoteDevice()->NodeMaps().at(0);
    }

    if (!m_device->NodeMaps().empty())
    {
        m_nodeMaps[NodeMapType::LocalDevice] = m_device->NodeMaps().at(0);
    }

    if (!m_dataStream->NodeMaps().empty())
    {
        m_nodeMaps[NodeMapType::Datastream] = m_dataStream->NodeMaps().at(0);
    }

    if (!m_device->ParentInterface()->NodeMaps().empty())
    {
        m_nodeMaps[NodeMapType::Interface] = m_device->ParentInterface()->NodeMaps().at(0);
    }

    if (!m_device->ParentInterface()->ParentSystem()->NodeMaps().empty())
    {
        m_nodeMaps[NodeMapType::System] = m_device->ParentInterface()->ParentSystem()->NodeMaps().at(0);
    }

    UpdateAcquisitionMode();
}

Camera::~Camera() noexcept
{
    try
    {
        if (m_dataStream && m_dataStream->IsGrabbing())
        {
            StopAcquisition();
        }
    }
    catch (const peak::core::Exception& e)
    {
        std::cout << "Camera::~Camera() raised an exception: " << e.what() << std::endl;
    }
}

Camera Camera::OpenFirstAvailable()
{
    return OpenWithCondition([](const std::shared_ptr<peak::core::DeviceDescriptor>&) {
        return true;
    });
}

Camera Camera::OpenBySerialNumber(const std::string& serial)
{
    return OpenWithCondition([serial](const std::shared_ptr<peak::core::DeviceDescriptor>& dev) {
        return dev->SerialNumber() == serial;
    });
}

Camera Camera::OpenWithCondition(const DeviceFilter& condition)
{
    auto& manager = peak::DeviceManager::Instance();
    manager.Update();

    const auto devices = manager.Devices();
    if (devices.empty())
    {
        throw std::runtime_error("No devices found");
    }

    constexpr auto accessType = peak::core::DeviceAccessType::Control;
    const auto deviceDescriptorIt = std::find_if(
        devices.begin(), devices.end(), [&condition, accessType](const auto& device) {
            return condition(device) && device->IsOpenable(accessType);
        });
    if (deviceDescriptorIt == devices.end())
    {
        throw std::runtime_error("No available device found");
    }

    return Camera((*deviceDescriptorIt)->OpenDevice(accessType));
}

std::shared_ptr<peak::core::NodeMap> Camera::GetNodeMap(NodeMapType type)
{
    const auto it = m_nodeMaps.find(type);
    if (it == m_nodeMaps.end())
    {
        throw std::runtime_error("Node map not available");
    }
    return it->second;
}

bool Camera::HasNode(const std::string& nodeName, NodeMapType nodeMapType)
{
    try
    {
        return GetNodeMap(nodeMapType)->HasNode(nodeName);
    }
    catch (const peak::core::Exception&)
    {
        return false;
    }
}

bool Camera::HasNodes(const std::vector<std::string>& nodeNames, NodeMapType nodeMapType)
{
    return std::all_of(nodeNames.cbegin(), nodeNames.cend(), [this, nodeMapType](const auto& name) {
        return HasNode(name, nodeMapType);
    });
}

bool Camera::HasEnumNodeEntry(const std::string& nodeName, const std::string& entryName)
{
    const auto node = GetNodeMap(NodeMapType::RemoteDevice)->FindNode<peak::core::nodes::EnumerationNode>(nodeName);
    const auto entryNode = node->TryFindEntry(entryName);
    return entryNode != nullptr && entryNode->IsAvailable();
}

void Camera::SetEnumNodeEntry(const std::string& nodeName, const std::string& entryName, NodeMapType nodeMapType)
{
    const auto node = GetNodeMap(nodeMapType)->FindNode<peak::core::nodes::EnumerationNode>(nodeName);
    node->SetCurrentEntry(entryName);
}

void Camera::SetNodeValue(const std::string& nodeName, const std::string& value, NodeMapType nodeMapType)
{
    const auto node = GetNodeMap(nodeMapType)->FindNode<peak::core::nodes::StringNode>(nodeName);
    node->SetValue(value);
}

void Camera::SetNodeValue(const std::string& nodeName, bool value, NodeMapType nodeMapType)
{
    const auto node = GetNodeMap(nodeMapType)->FindNode<peak::core::nodes::BooleanNode>(nodeName);
    node->SetValue(value);
}

void Camera::SetNodeValue(const std::string& nodeName, int64_t value, NodeMapType nodeMapType)
{
    const auto node = GetNodeMap(nodeMapType)->FindNode<peak::core::nodes::IntegerNode>(nodeName);
    node->SetValue(value);
}

void Camera::SetNodeValue(const std::string& nodeName, double value, NodeMapType nodeMapType)
{
    const auto node = GetNodeMap(nodeMapType)->FindNode<peak::core::nodes::FloatNode>(nodeName);
    node->SetValue(value);
}

std::string Camera::GetNodeValueString(const std::string& nodeName, NodeMapType nodeMapType)
{
    const auto node = GetNodeMap(nodeMapType)->FindNode(nodeName);
    if (node->Type() == peak::core::nodes::NodeType::String)
    {
        return std::dynamic_pointer_cast<peak::core::nodes::StringNode>(node)->Value();
    }

    if (node->Type() == peak::core::nodes::NodeType::Enumeration)
    {
        return std::dynamic_pointer_cast<peak::core::nodes::EnumerationNode>(node)->CurrentEntry()->SymbolicValue();
    }

    throw std::runtime_error("Node is neither a string nor an enumeration node.");
}

bool Camera::GetNodeValueBool(const std::string& nodeName, NodeMapType nodeMapType)
{
    return GetNodeMap(nodeMapType)->FindNode<peak::core::nodes::BooleanNode>(nodeName)->Value();
}

int64_t Camera::GetNodeValueInt(const std::string& nodeName, NodeMapType nodeMapType)
{
    return GetNodeMap(nodeMapType)->FindNode<peak::core::nodes::IntegerNode>(nodeName)->Value();
}

double Camera::GetNodeValueFloat(const std::string& name, NodeMapType nodeMapType)
{
    return GetNodeMap(nodeMapType)->FindNode<peak::core::nodes::FloatNode>(name)->Value();
}

void Camera::ExecCommandNodeAndWait(const std::string& nodeName, NodeMapType nodeMapType)
{
    const auto node = GetNodeMap(nodeMapType)->FindNode<peak::core::nodes::CommandNode>(nodeName);
    node->Execute();
    node->WaitUntilDone();
}

void Camera::LoadUserSet(UserSet userSet)
{
    SetEnumNodeEntry("UserSetSelector", UserSetToString(userSet));
    ExecCommandNodeAndWait("UserSetLoad");
    UpdateAcquisitionMode();
}

void Camera::ResetToDefault()
{
    LoadUserSet(UserSet::Default);
    UpdateAcquisitionMode();
}

void Camera::UpdateAcquisitionMode()
{
    const auto nodeMap = GetNodeMap(NodeMapType::RemoteDevice);

    const auto acquisitionModeNode = nodeMap->FindNode<peak::core::nodes::EnumerationNode>("AcquisitionMode");
    const auto acquisitionMode = acquisitionModeNode->CurrentEntry()->SymbolicValue();

    if (acquisitionMode == "SingleFrame")
    {
        m_acquisitionFrameCount = 1U;
    }
    else if (acquisitionMode == "MultiFrame")
    {
        const auto acquisitionFrameCountNode = nodeMap->FindNode<peak::core::nodes::IntegerNode>(
            "AcquisitionFrameCount");
        m_acquisitionFrameCount = static_cast<uint64_t>(acquisitionFrameCountNode->Value());
    }
    else
    {
        m_acquisitionFrameCount = peak::core::DataStream::INFINITE_NUMBER;
    }

    const auto triggerSelector = nodeMap->FindNode<peak::core::nodes::EnumerationNode>("TriggerSelector");
    const auto triggerMode = nodeMap->FindNode<peak::core::nodes::EnumerationNode>("TriggerMode");
    const auto triggerSource = nodeMap->FindNode<peak::core::nodes::EnumerationNode>("TriggerSource");

    // Convert available entries to string vector for easier search
    const auto availableEntries = GetEnumEntriesAsStrings(triggerSelector->AvailableEntries());

    m_acquisitionMode = AcquisitionMode::Freerun;

    const auto availableFrameStartTriggers = FindAvailableFrameStartTriggers(availableEntries);
    for (const auto& trigger : availableFrameStartTriggers)
    {
        triggerSelector->SetCurrentEntry(trigger);

        if (triggerMode->CurrentEntry()->SymbolicValue() != "On")
        {
            continue;
        }

        m_acquisitionMode = triggerSource->CurrentEntry()->SymbolicValue() == "Software" ?
            AcquisitionMode::SoftwareTrigger :
            AcquisitionMode::Unknown;
        break;
    }
}

void Camera::LockTlParams(bool lock)
{
    const auto value = static_cast<int64_t>(lock ? 1 : 0);
    SetNodeValue("TLParamsLocked", value);
}

void Camera::SetAcquisitionFrameCount(int64_t frameCount)
{
    auto frameCountNode = GetNodeMap(NodeMapType::RemoteDevice)
                              ->FindNode<peak::core::nodes::IntegerNode>("AcquisitionFrameCount");
    if (frameCount == 1)
    {
        SetEnumNodeEntry("AcquisitionMode", "SingleFrame");
    }
    else if (frameCount > frameCountNode->Maximum())
    {
        SetEnumNodeEntry("AcquisitionMode", "Continuous");
    }
    else
    {
        SetEnumNodeEntry("AcquisitionMode", "MultiFrame");
        frameCountNode->SetValue(frameCount);
    }
    m_acquisitionFrameCount = static_cast<uint64_t>(frameCount);
}

void Camera::StartAcquisition(size_t bufferCountHint)
{
    AllocBuffers(std::max(bufferCountHint, m_dataStream->NumBuffersAnnouncedMinRequired()));

    LockTlParams(true);
    m_dataStream->StartAcquisition(peak::core::AcquisitionStartMode::Default, m_acquisitionFrameCount);
    ExecCommandNodeAndWait("AcquisitionStart");
}

void Camera::StopAcquisition()
{
    ExecCommandNodeAndWait("AcquisitionStop");
    m_dataStream->StopAcquisition();
    LockTlParams(false);
}

std::shared_ptr<peak::core::Buffer> Camera::AcquireImageBuffer(peak::core::Timeout timeout)
{
    if (m_acquisitionMode == AcquisitionMode::SoftwareTrigger)
    {
        ExecuteSoftwareTrigger();
    }
    return m_dataStream->WaitForFinishedBuffer(timeout);
}

void Camera::QueueBuffer(const std::shared_ptr<peak::core::Buffer>& buffer) const
{
    m_dataStream->QueueBuffer(buffer);
}

void Camera::RevokeBuffers() const
{
    m_dataStream->Flush(peak::core::DataStreamFlushMode::AllToInputPool);
    for (const auto& buffer : m_dataStream->AnnouncedBuffers())
    {
        m_dataStream->RevokeBuffer(buffer);
    }
}

void Camera::AllocBuffers(size_t numBuffers)
{
    RevokeBuffers();

    const auto payloadSize = m_dataStream->DefinesPayloadSize() ? m_dataStream->PayloadSize() :
                                                                  static_cast<size_t>(GetNodeValueInt("PayloadSize"));

    for (size_t i = 0; i < numBuffers; ++i)
    {
        auto buffer = m_dataStream->AllocAndAnnounceBuffer(payloadSize, nullptr);
        m_dataStream->QueueBuffer(buffer);
    }
}

void Camera::SetAcquisitionMode(AcquisitionMode mode)
{
    if (mode != AcquisitionMode::Freerun && mode != AcquisitionMode::SoftwareTrigger)
    {
        throw std::runtime_error("Acquisition mode is not supported.");
    }

    const auto nodeMap = GetNodeMap(NodeMapType::RemoteDevice);
    const auto triggerSelector = nodeMap->FindNode<peak::core::nodes::EnumerationNode>("TriggerSelector");
    const auto triggerMode = nodeMap->FindNode<peak::core::nodes::EnumerationNode>("TriggerMode");

    const auto availableEntries = GetEnumEntriesAsStrings(triggerSelector->AvailableEntries());

    // Disable all frame start triggers
    const auto availableFrameStartTriggers = FindAvailableFrameStartTriggers(availableEntries);
    for (const auto& entry : availableFrameStartTriggers)
    {
        triggerSelector->SetCurrentEntry(entry);
        if (triggerMode->CurrentEntry()->SymbolicValue() != "Off" && triggerMode->IsWriteable())
        {
            triggerMode->SetCurrentEntry("Off");
        }
    }

    if (mode == AcquisitionMode::SoftwareTrigger)
    {
        // Find first available frame start trigger
        const std::string trigger = FindPreferredFrameStartTrigger(availableEntries);
        triggerSelector->SetCurrentEntry(trigger);
        SetEnumNodeEntry("TriggerSource", "Software");
        triggerMode->SetCurrentEntry("On");
    }

    m_acquisitionMode = mode;
}

void Camera::ExecuteSoftwareTrigger()
{
    ExecCommandNodeAndWait("TriggerSoftware");
}
} // namespace hdr
