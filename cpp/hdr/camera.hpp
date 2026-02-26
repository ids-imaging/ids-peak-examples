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

#pragma once

#include <peak/peak.hpp>

#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace hdr
{

/** Camera image acquisition modes. */
enum class AcquisitionMode
{
    Unknown = -1,
    Freerun = 0,
    SoftwareTrigger = 1
};

/** Node map types. */
enum class NodeMapType
{
    RemoteDevice = 0,
    LocalDevice = 1,
    Datastream = 2,
    Interface = 3,
    System = 4
};

/** Camera UserSets. */
enum class UserSet
{
    Default = 0,
    HighSpeed = 1,
    Linescan = 2,
    LinescanHighSpeed = 3,
    LongExposure = 4,
    UserSet0 = 5,
    UserSet1 = 6,
    QuadHdr = 7,
    ClearHdr = 8,
};

/** Wraps a device object to expose additional camera-specific features. */
class Camera
{
public:
    using DeviceFilter = std::function<bool(const std::shared_ptr<peak::core::DeviceDescriptor>&)>;

    explicit Camera(const std::shared_ptr<peak::core::Device>& device);

    Camera(const Camera&) = delete;
    Camera& operator=(const Camera&) = delete;

    Camera(Camera&&) noexcept = default;
    Camera& operator=(Camera&&) noexcept = default;

    ~Camera() noexcept;

    /** Open first available camera. */
    static Camera OpenFirstAvailable();

    /** Open camera by serial number. */
    static Camera OpenBySerialNumber(const std::string& serial);

    /** Return true if a node with the given name exists. */
    bool HasNode(const std::string& nodeName, NodeMapType nodeMapType = NodeMapType::RemoteDevice);

    /** Return true if all nodes in the given list exist. */
    bool HasNodes(const std::vector<std::string>& nodeNames, NodeMapType nodeMapType = NodeMapType::RemoteDevice);

    /** Check if the specified enumeration node contains the given entry. */
    bool HasEnumNodeEntry(const std::string& nodeName, const std::string& entryName);

    /** Assign the given entry to the specified enumeration node. */
    void SetEnumNodeEntry(
        const std::string& nodeName, const std::string& entryName, NodeMapType nodeMapType = NodeMapType::RemoteDevice);

    /** Assign the given string value to the specified string node. */
    void SetNodeValue(
        const std::string& nodeName, const std::string& value, NodeMapType nodeMapType = NodeMapType::RemoteDevice);

    /** Assign the given bool value to the specified boolean node. */
    void SetNodeValue(const std::string& nodeName, bool value, NodeMapType nodeMapType = NodeMapType::RemoteDevice);

    /** Assign the given int value to the specified integer node. */
    void SetNodeValue(const std::string& nodeName, int64_t value, NodeMapType nodeMapType = NodeMapType::RemoteDevice);

    /** Assign the given double value to the specified float node. */
    void SetNodeValue(const std::string& nodeName, double value, NodeMapType nodeMapType = NodeMapType::RemoteDevice);

    /** Return the string value of the specified string or enumeration node. */
    std::string GetNodeValueString(const std::string& nodeName, NodeMapType nodeMapType = NodeMapType::RemoteDevice);

    /** Return the bool value of the specified boolean node. */
    bool GetNodeValueBool(const std::string& nodeName, NodeMapType nodeMapType = NodeMapType::RemoteDevice);

    /** Return the int value of the specified integer node. */
    int64_t GetNodeValueInt(const std::string& nodeName, NodeMapType nodeMapType = NodeMapType::RemoteDevice);

    /** Return the double value of the specified float node. */
    double GetNodeValueFloat(const std::string& name, NodeMapType nodeMapType = NodeMapType::RemoteDevice);

    /** Execute the specified command and wait for it to complete. */
    void ExecCommandNodeAndWait(const std::string& nodeName, NodeMapType nodeMapType = NodeMapType::RemoteDevice);

    /** Load the specified user set. */
    void LoadUserSet(UserSet userSet);

    /** Load user set 'Default'. */
    void ResetToDefault();

    /**
     * \brief Configure the number of frames to be acquired.
     *
     * @param frameCount The requested number of frames to capture. Depending on this value,
            the camera operates in one of the following modes:
            - SingleFrame: count == 1
            - MultiFrame: 1 < count <= maximum supported frame count
            - Continuous: count exceeds the maximum supported frame count for MultiFrame acquisition
     */
    void SetAcquisitionFrameCount(int64_t frameCount);

    /**
     * \brief Start acquisition.
     *
     * @param bufferCountHint  Suggested minimum number of buffers to allocate for acquisition.
     *                         The actual allocated buffer count may be higher.
     */
    void StartAcquisition(size_t bufferCountHint = 5);

    /** Stop acquisition. */
    void StopAcquisition();

    /**
     * \brief Acquire an image buffer from the camera.
     *
     * If the camera is configured for software trigger mode, a software
     * trigger is executed before acquiring the buffer.
     *
     * @param timeout  Maximum time to wait for the buffer, in milliseconds.
     */
    std::shared_ptr<peak::core::Buffer> AcquireImageBuffer(peak::core::Timeout timeout);

    /** Re-queue a buffer that is no longer needed. */
    void QueueBuffer(const std::shared_ptr<peak::core::Buffer>& buffer) const;

    /** Set acquisition mode. */
    void SetAcquisitionMode(AcquisitionMode mode);

    /** The wrapped device. */
    std::shared_ptr<peak::core::Device> Device() const
    {
        return m_device;
    }

private:
    static Camera OpenWithCondition(const DeviceFilter& condition);

    void UpdateAcquisitionMode();

    void LockTlParams(bool lock);

    void AllocBuffers(size_t numBuffers);

    void RevokeBuffers() const;

    void ExecuteSoftwareTrigger();

    std::shared_ptr<peak::core::NodeMap> GetNodeMap(NodeMapType type);

    std::shared_ptr<peak::core::Device> m_device{};
    std::shared_ptr<peak::core::DataStream> m_dataStream{};
    std::unordered_map<NodeMapType, std::shared_ptr<peak::core::NodeMap>> m_nodeMaps{};
    AcquisitionMode m_acquisitionMode{ AcquisitionMode::Unknown };
    uint64_t m_acquisitionFrameCount{ peak::core::DataStream::INFINITE_NUMBER };
};
} // namespace hdr
