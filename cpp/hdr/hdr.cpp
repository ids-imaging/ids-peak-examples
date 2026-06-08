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

#include "hdr.hpp"
#include "hdr_utils.hpp"

#include <peak_icv/algorithms/hdr/peak_icv_hdr.hpp>
#include <peak_icv/algorithms/hdr/tone_mapping/peak_icv_drago_tone_mapping.hpp>

#include <array>
#include <chrono>
#include <regex>
#include <stdexcept>

using namespace std::chrono_literals;

namespace hdr
{

std::string HdrAcquisitionModeToString(HdrAcquisitionMode mode)
{
    switch (mode)
    {
    case HdrAcquisitionMode::Auto:
        return "AUTO";

    case HdrAcquisitionMode::Progressive:
        return "PROGRESSIVE";

    case HdrAcquisitionMode::Sequencer:
        return "SEQUENCER";

    case HdrAcquisitionMode::QuadExposure:
        return "QUAD_EXPOSURE";

    case HdrAcquisitionMode::ClearHdr:
        return "CLEAR_HDR";

    default:
        return "UNKNOWN";
    }
}

HdrAcquisitionMode StringToHdrAcquisitionMode(const std::string& str)
{
    if (str == "AUTO")
    {
        return HdrAcquisitionMode::Auto;
    }
    if (str == "PROGRESSIVE")
    {
        return HdrAcquisitionMode::Progressive;
    }
    if (str == "SEQUENCER")
    {
        return HdrAcquisitionMode::Sequencer;
    }
    if (str == "QUAD_EXPOSURE")
    {
        return HdrAcquisitionMode::QuadExposure;
    }
    if (str == "CLEAR_HDR")
    {
        return HdrAcquisitionMode::ClearHdr;
    }
    throw std::invalid_argument("Unknown HdrAcquisitionMode string: " + str);
}

peak::icv::Image ProcessImage(const peak::icv::Image& inputImage)
{
    const auto image = peak::icv::Image(inputImage);
    if (image.GetPixelFormat() == peak::common::PixelFormat::Mono8
        || image.GetPixelFormat() == peak::common::PixelFormat::RGB8)
    {
        return image.Copy();
    }

    const auto info = peak::common::PixelFormatInfo(inputImage.GetPixelFormat());
    constexpr std::array<peak::common::Channel, 3> colorChannels{ peak::common::Channel::Red,
        peak::common::Channel::Bayer, peak::common::Channel::ChromaU };
    const auto& channels = info.GetChannels();
    if (std::any_of(colorChannels.cbegin(), colorChannels.cend(), [&channels](const auto& colorChannel) {
            return std::find(channels.cbegin(), channels.cend(), colorChannel) != channels.cend();
        }))
    {
        return image.ConvertPixelFormat(peak::common::PixelFormat::RGB8);
    }

    if (info.HasIntensityChannel())
    {
        return image.ConvertPixelFormat(peak::common::PixelFormat::Mono8);
    }

    throw std::runtime_error("Unsupported pixel format!");
}

ImageSequence ProcessInterleavedImage(const peak::icv::Image& image)
{
    auto imageSequence = image.Deinterleave();
    std::transform(imageSequence.cbegin(), imageSequence.cend(), imageSequence.begin(), [](auto& img) {
        return ProcessImage(img);
    });
    return imageSequence;
}

ExposureSequence CreateExposureSequence(
    const IntervalD& exposureRange_s, size_t numExposures) // NOLINT(readability-identifier-naming)
{
    if (numExposures < 2)
    {
        throw std::invalid_argument("Exposure sequence must be at least two");
    }
    ExposureSequence exposures;
    exposures.reserve(numExposures);

    const auto logMin = std::log10(exposureRange_s.GetMinimum());
    const auto logMax = std::log10(exposureRange_s.GetMaximum());
    const auto step = (logMax - logMin) / static_cast<double>(numExposures - 1);

    for (size_t i = 0; i < numExposures; ++i)
    {
        const auto val = std::pow(10.0, logMin + (static_cast<double>(i) * step));
        exposures.emplace_back(val);
    }
    return exposures;
}

HdrResult ComputeHdr(const ImageSequence& imageSequence)
{
    const peak::icv::HDR hdrProcessor;
    const auto hdrImage = hdrProcessor.Process(imageSequence);

    const peak::icv::DragoToneMapping toneMapper;
    const auto ldrImage = toneMapper.Process(hdrImage);

    return { imageSequence, hdrImage, ldrImage };
}

HdrResult CalculateHdrImageFromDirectory(const std::string& path)
{
    ImageSequence imageSequence;

    // Pattern: seq\d+_\d+ms\d+\.png
    const std::regex pattern(R"(^seq\d+_(\d+)ms(\d+)\.png$)");

    // Iterate through directory
    for (const auto& filePath : utils::ListRegularFiles(path))
    {
        std::smatch match;

        const auto fileName = utils::GetFilename(filePath);
        if (std::regex_match(fileName, match, pattern))
        {
            // Extract exposure time from filename
            const auto major_ms =    // NOLINT(readability-identifier-naming)
                match[1].str();
            const auto minor_ms =    // NOLINT(readability-identifier-naming)
                match[2].str();

            const auto exposure_us = // NOLINT(readability-identifier-naming)
                utils::MakeDecimal(major_ms, minor_ms) * 1'000.0;

            auto image = peak::icv::Image(filePath);
            auto metadata = image.GetMetadata();
            metadata.SetValueByKey<peak::common::MetadataKey::DeviceExposureTime>(exposure_us);
            image.SetMetadata(metadata);
            imageSequence.emplace_back(image);
        }
    }

    if (imageSequence.empty())
    {
        throw std::runtime_error("No valid image files found in directory: " + path);
    }

    return ComputeHdr(imageSequence);
}

// ProgressiveHdrProvider

ProgressiveHdrProvider::ProgressiveHdrProvider(const std::shared_ptr<Camera>& camera)
    : m_camera{ camera }
{}

HdrAcquisitionMode ProgressiveHdrProvider::Mode() const
{
    return HdrAcquisitionMode::Progressive;
}

bool ProgressiveHdrProvider::IsSupported() const
{
    return true;
}

void ProgressiveHdrProvider::Configure(
    const ExposureSequence& exposureSequence_s) // NOLINT(readability-identifier-naming)
{
    if (exposureSequence_s.size() < 2)
    {
        throw std::invalid_argument("A HDR image consists of at least 2 exposures.");
    }
    m_deviceExposureSequence_s = exposureSequence_s;
    m_camera->SetAcquisitionMode(AcquisitionMode::SoftwareTrigger);
}

HdrResult ProgressiveHdrProvider::AcquireHdrImage()
{
    if (!IsSupported() || m_deviceExposureSequence_s.size() < 2)
    {
        throw std::runtime_error("HDR provider is not supported or configured!");
    }

    m_camera->StartAcquisition(m_deviceExposureSequence_s.size());

    const auto imageSequence = AcquireHdrSequence();

    m_camera->StopAcquisition();

    return ComputeHdr(imageSequence);
}

ImageSequence ProgressiveHdrProvider::AcquireHdrSequence()
{
    if (!IsSupported() || m_deviceExposureSequence_s.size() < 2)
    {
        throw std::runtime_error("HDR provider is not supported or configured!");
    }

    ImageSequence imageSequence;
    imageSequence.reserve(m_deviceExposureSequence_s.size());
    const peak::core::Timeout timeout(5s);

    for (const auto& exposure_s : m_deviceExposureSequence_s) // NOLINT(readability-identifier-naming)
    {
        const auto exposure_us = exposure_s * 1'000'000.0;    // NOLINT(readability-identifier-naming)
        m_camera->SetNodeValue("ExposureTime", exposure_us);

        const auto buffer = m_camera->AcquireImageBuffer(timeout);

        auto image = ProcessImage(peak::icv::Image(buffer->ToImageView()));
        auto imageMetadata = image.GetMetadata();
        imageMetadata.SetValueByKey<peak::common::MetadataKey::DeviceExposureTime>(
            m_camera->GetNodeValueFloat("ExposureTime"));
        image.SetMetadata(imageMetadata);
        imageSequence.emplace_back(image);

        m_camera->QueueBuffer(buffer);
    }

    return imageSequence;
}

// SequencerHdrProvider

SequencerHdrProvider::SequencerHdrProvider(const std::shared_ptr<Camera>& camera)
    : m_camera{ camera }
    , m_supported{ CheckHdrSupported() }
{}

HdrAcquisitionMode SequencerHdrProvider::Mode() const
{
    return HdrAcquisitionMode::Sequencer;
}

bool SequencerHdrProvider::CheckHdrSupported() const
{
    const std::vector<std::string> sequencerNodes = { "SequencerFeatureSelector", "SequencerFeatureEnable",
        "SequencerConfigurationMode", "SequencerSetSelector", "SequencerSetNext", "SequencerPathSelector",
        "SequencerTriggerSource", "SequencerTriggerActivation", "SequencerSetSave", "SequencerMode" };

    if (!m_camera->HasNodes(sequencerNodes))
    {
        return false;
    }

    try
    {
        m_camera->SetEnumNodeEntry("SequencerConfigurationMode", "On");
        m_camera->SetEnumNodeEntry("SequencerFeatureSelector", "ExposureTime");

        if (!m_camera->GetNodeValueBool("SequencerFeatureEnable"))
        {
            m_camera->SetNodeValue("SequencerFeatureEnable", true);
        }

        m_camera->SetEnumNodeEntry("SequencerConfigurationMode", "Off");
        return true;
    }
    catch (const peak::core::Exception&)
    {
        return false;
    }
}

bool SequencerHdrProvider::IsSupported() const
{
    return m_supported;
}

void SequencerHdrProvider::Configure(
    const ExposureSequence& exposureSequence_s) // NOLINT(readability-identifier-naming)
{
    if (exposureSequence_s.size() < 2)
    {
        throw std::invalid_argument("A HDR image consists of at least 2 exposures.");
    }

    try
    {
        m_camera->SetEnumNodeEntry("SequencerMode", "Off");
    }
    catch (const peak::core::Exception& e)
    {
        (void)e; // ignored - sequencer mode might be already off
    }

    m_deviceExposureSequence_s.clear();

    m_camera->SetEnumNodeEntry("SequencerConfigurationMode", "On");

    for (size_t i = 0; i < exposureSequence_s.size(); ++i)
    {
        const size_t idxNext = (i + 1) % exposureSequence_s.size();

        m_camera->SetNodeValue("SequencerSetSelector", static_cast<int64_t>(i));
        m_camera->SetNodeValue("SequencerPathSelector", static_cast<int64_t>(0));
        m_camera->SetNodeValue("SequencerSetNext", static_cast<int64_t>(idxNext));

        m_camera->SetEnumNodeEntry("SequencerTriggerSource", "ExposureStart");
        m_camera->SetEnumNodeEntry("SequencerTriggerActivation", "RisingEdge");

        const auto exposure_us = // NOLINT(readability-identifier-naming)
            exposureSequence_s.at(i) * 1'000'000.0;
        m_camera->SetNodeValue("ExposureTime", exposure_us);

        m_deviceExposureSequence_s.push_back(
            static_cast<float>(m_camera->GetNodeValueFloat("ExposureTime")) / 1'000'000.0F);

        m_camera->ExecCommandNodeAndWait("SequencerSetSave");
    }

    m_camera->SetEnumNodeEntry("SequencerConfigurationMode", "Off");
    m_camera->SetAcquisitionMode(AcquisitionMode::SoftwareTrigger);
    m_camera->SetEnumNodeEntry("SequencerMode", "On");
}

HdrResult SequencerHdrProvider::AcquireHdrImage()
{
    if (!IsSupported() || m_deviceExposureSequence_s.size() < 2)
    {
        throw std::runtime_error("HDR provider is not supported or configured!");
    }

    m_camera->StartAcquisition(m_deviceExposureSequence_s.size());

    const auto imageSequence = AcquireHdrSequence();

    m_camera->StopAcquisition();

    return ComputeHdr(imageSequence);
}

ImageSequence SequencerHdrProvider::AcquireHdrSequence()
{
    if (!IsSupported() || m_deviceExposureSequence_s.size() < 2)
    {
        throw std::runtime_error("HDR provider is not supported or configured!");
    }

    ImageSequence imageSequence;
    imageSequence.reserve(m_deviceExposureSequence_s.size());
    const peak::core::Timeout timeout(5s);

    for (const auto& deviceExposure_s : m_deviceExposureSequence_s) // NOLINT(readability-identifier-naming)
    {
        const auto buffer = m_camera->AcquireImageBuffer(timeout);

        auto image = ProcessImage(peak::icv::Image(buffer->ToImageView()));
        auto imageMetadata = image.GetMetadata();
        imageMetadata.SetValueByKey<peak::common::MetadataKey::DeviceExposureTime>(deviceExposure_s * 1'000'000);
        image.SetMetadata(imageMetadata);
        imageSequence.emplace_back(image);

        m_camera->QueueBuffer(buffer);
    }

    return imageSequence;
}

// QuadExposureHdrProvider

QuadExposureHdrProvider::QuadExposureHdrProvider(const std::shared_ptr<Camera>& camera)
    : m_camera{ camera }
    , m_supported{ CheckHdrSupported() }
{}

HdrAcquisitionMode QuadExposureHdrProvider::Mode() const
{
    return HdrAcquisitionMode::QuadExposure;
}

bool QuadExposureHdrProvider::CheckHdrSupported() const
{
    return m_camera->HasEnumNodeEntry("UserSetSelector", "QuadHDR");
}

bool QuadExposureHdrProvider::IsSupported() const
{
    return m_supported;
}

void QuadExposureHdrProvider::Configure(
    const ExposureSequence& exposureSequence_s) // NOLINT(readability-identifier-naming)
{
    if (exposureSequence_s.size() != 4)
    {
        throw std::runtime_error("Quad exposure needs exactly 4 exposures.");
    }

    m_deviceExposureSequence_s.clear();

    m_camera->LoadUserSet(UserSet::QuadHdr);

    const auto exposureTimeSelectorEntries = std::array<std::string, 4>{ "Pixel1", "Pixel2", "Pixel3", "Pixel4" };
    for (size_t i = 0; i < exposureSequence_s.size(); ++i)
    {
        m_camera->SetEnumNodeEntry("ExposureTimeSelector", exposureTimeSelectorEntries.at(i));
        const auto exposure_us = exposureSequence_s.at(i) * 1'000'000; // NOLINT(readability-identifier-naming)
        m_camera->SetNodeValue("ExposureTime", exposure_us);

        m_deviceExposureSequence_s.emplace_back(
            static_cast<float>(m_camera->GetNodeValueFloat("ExposureTime")) / 1'000'000.0F);
    }

    m_camera->SetAcquisitionMode(AcquisitionMode::Freerun);
    m_camera->SetAcquisitionFrameCount(1);
}

HdrResult QuadExposureHdrProvider::AcquireHdrImage()
{
    if (!IsSupported() || m_deviceExposureSequence_s.size() != 4)
    {
        throw std::runtime_error("HDR provider is not supported or configured!");
    }

    m_camera->StartAcquisition(1);

    const auto imageSequence = AcquireHdrSequence();

    m_camera->StopAcquisition();

    return ComputeHdr(imageSequence);
}

ImageSequence QuadExposureHdrProvider::AcquireHdrSequence()
{
    if (!IsSupported() || m_deviceExposureSequence_s.size() != 4)
    {
        throw std::runtime_error("HDR provider is not supported or configured!");
    }

    const peak::core::Timeout timeout(5s);

    const auto buffer = m_camera->AcquireImageBuffer(timeout);
    auto image = peak::icv::Image(buffer->ToImageView());

    auto exposureSequence_us = std::vector<double>();              // NOLINT(readability-identifier-naming)
    exposureSequence_us.reserve(m_deviceExposureSequence_s.size());
    for (const double exposureTime_s : m_deviceExposureSequence_s) // NOLINT(readability-identifier-naming)
    {
        exposureSequence_us.emplace_back(exposureTime_s * 1'000'000.0);
    }

    auto metadata = image.GetMetadata();
    metadata.SetValueByKey<peak::common::MetadataKey::DeviceExposureTimeSequence>(exposureSequence_us);
    image.SetMetadata(metadata);

    const auto imageSequence = ProcessInterleavedImage(image);
    m_camera->QueueBuffer(buffer);

    return imageSequence;
}

// ClearHdrProvider

ClearHdrProvider::ClearHdrProvider(const std::shared_ptr<Camera>& camera)
    : m_camera{ camera }
    , m_supported{ CheckHdrSupported() }
{}

HdrAcquisitionMode ClearHdrProvider::Mode() const
{
    return HdrAcquisitionMode::ClearHdr;
}

bool ClearHdrProvider::CheckHdrSupported() const
{
    return m_camera->HasEnumNodeEntry("UserSetSelector", "ClearHDR");
}

bool ClearHdrProvider::IsSupported() const
{
    return m_supported;
}

void ClearHdrProvider::Configure(const ExposureSequence& exposureSequence_s) // NOLINT(readability-identifier-naming)
{
    if (exposureSequence_s.size() != 2)
    {
        throw std::runtime_error("Clear hdr needs exactly 2 exposures.");
    }

    m_deviceGains.clear();

    m_camera->LoadUserSet(UserSet::ClearHdr);

    // set first as exposure
    const auto firstExposure_s = exposureSequence_s.at(0);                      // NOLINT(readability-identifier-naming)
    m_camera->SetNodeValue("ExposureTime", firstExposure_s * 1'000'000);
    const auto deviceExposure_us = m_camera->GetNodeValueFloat("ExposureTime"); // NOLINT(readability-identifier-naming)
    m_deviceExposure_s = deviceExposure_us / 1'000'000;

    // set first gain value to 1.0
    m_camera->SetEnumNodeEntry("GainSelector", "AnalogLow");
    m_camera->SetNodeValue("Gain", 1.0);

    // calculate gain factor from second exposure
    const auto highGainFactor = exposureSequence_s.at(1) / firstExposure_s;

    // set second gain factor to calculated value
    m_camera->SetEnumNodeEntry("GainSelector", "AnalogHigh");
    m_camera->SetNodeValue("Gain", highGainFactor);

    const auto deviceGainFactor = m_camera->GetNodeValueFloat("Gain");

    m_deviceGains.emplace_back(deviceGainFactor);
    // lower gain needs to be second in the list,
    // because the image sequence starts with the higher gain
    m_deviceGains.emplace_back(1.0);

    m_camera->SetAcquisitionMode(AcquisitionMode::Freerun);
    m_camera->SetAcquisitionFrameCount(1);
}

HdrResult ClearHdrProvider::AcquireHdrImage()
{
    if (!IsSupported() || m_deviceGains.size() != 2)
    {
        throw std::runtime_error("HDR provider is not supported or configured!");
    }

    m_camera->StartAcquisition(1);

    const auto imageSequence = AcquireHdrSequence();

    m_camera->StopAcquisition();

    return ComputeHdr(imageSequence);
}

ImageSequence ClearHdrProvider::AcquireHdrSequence()
{
    if (!IsSupported() || m_deviceGains.size() != 2)
    {
        throw std::runtime_error("HDR provider is not supported or configured!");
    }

    const peak::core::Timeout timeout(5s);

    const auto buffer = m_camera->AcquireImageBuffer(timeout);
    auto image = peak::icv::Image(buffer->ToImageView());

    auto metadata = image.GetMetadata();
    metadata.SetValueByKey<peak::common::MetadataKey::DeviceExposureTime>(m_deviceExposure_s * 1'000'000.0);
    metadata.SetValueByKey<peak::common::MetadataKey::DeviceGainSequence>(m_deviceGains);
    image.SetMetadata(metadata);

    const auto imageSequence = ProcessInterleavedImage(image);
    m_camera->QueueBuffer(buffer);

    return imageSequence;
}

// HdrRegistry

HdrProviderRegistry::HdrProviderRegistry(const std::shared_ptr<Camera>& camera)
{
    m_providers.emplace_back(std::make_shared<ClearHdrProvider>(camera));
    m_providers.emplace_back(std::make_shared<QuadExposureHdrProvider>(camera));
    m_providers.emplace_back(std::make_shared<SequencerHdrProvider>(camera));
    m_providers.emplace_back(std::make_shared<ProgressiveHdrProvider>(camera));
}

const std::vector<std::shared_ptr<IHdrProvider>>& HdrProviderRegistry::Providers() const
{
    return m_providers;
}

std::shared_ptr<IHdrProvider> HdrProviderRegistry::GetProvider(HdrAcquisitionMode hdrAcquisitionMode) const
{
    const auto providerIt = std::find_if(
        m_providers.begin(), m_providers.end(), [hdrAcquisitionMode](const auto& provider) {
            return provider->IsSupported()
                && (hdrAcquisitionMode == HdrAcquisitionMode::Auto || provider->Mode() == hdrAcquisitionMode);
        });
    if (providerIt != m_providers.end())
    {
        return *providerIt;
    }
    throw std::runtime_error("No supported provider");
}

std::shared_ptr<IHdrProvider> HdrProviderRegistry::PreferredProvider() const
{
    return GetProvider(HdrAcquisitionMode::Auto);
}
} // namespace hdr
