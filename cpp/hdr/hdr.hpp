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

#include "camera.hpp"

#include <peak_icv/peak_icv.hpp>

#include <memory>
#include <string>
#include <vector>

namespace hdr
{

using ImageSequence = std::vector<peak::icv::Image>;
using ExposureSequence = std::vector<double>;

using IntervalD = peak::common::detail::IntervalT<double>;

/** HDR acquisition modes */
enum class HdrAcquisitionMode
{
    /** Automatically selects the best available acquisition mode. */
    Auto = 0,

    /**
     * In progressive mode the exposure value is changed programmatically before
     * each image is captured.
     * This mode works for every camera that changes exposure instantly.
     */
    Progressive = 1,

    /**
     * Sequencer mode uses the camera's sequencer feature which is preconfigured
     * for the given exposure times.
     */
    Sequencer = 2,

    /**
     * Sensor feature for IMX900-based cameras that capture a single image
     * using four distinct exposure times arranged in a 2×2 pixel pattern.
     */
    QuadExposure = 3,

    /**
     * Sensor feature for IMX675-based cameras that capture a single image
     * using two gain factors in alternating lines starting with lower gain.
     */
    ClearHdr = 4,
};

std::string HdrAcquisitionModeToString(HdrAcquisitionMode mode);
HdrAcquisitionMode StringToHdrAcquisitionMode(const std::string& str);

inline std::ostream& operator<<(std::ostream& os, HdrAcquisitionMode m)
{
    return os << HdrAcquisitionModeToString(m);
}

/** Create an RGB8 or Mono8 ICV image from an input image, ensuring that the data is copied. */
peak::icv::Image ProcessImage(const peak::icv::Image& inputImage);

/** Return a logarithmically spaced sequence of exposure times. */
ExposureSequence CreateExposureSequence(
    const IntervalD& exposureRange_s, size_t numExposures); // NOLINT(readability-identifier-naming)

/** Result of an HDR capture operation */
struct HdrResult
{
    ImageSequence imageSequence;
    peak::icv::Image hdrImage;
    peak::icv::Image ldrImage;
};

/**
 * \brief Compute HDR and LDR images from an input image sequence.
 *
 * The input images are combined into a single HDR image, which is then
 * tone-mapped to produce a corresponding LDR image.
 *
 * @param imageSequence  Sequence of images captured with different exposure settings.
 *
 * @return An `HdrCaptureResult` containing the original image sequence,
 *         the computed HDR image, and the tone-mapped LDR image.
 */
HdrResult ComputeHdr(const ImageSequence& imageSequence);

/** Read images from the given path and calculate the HDR image. */
HdrResult CalculateHdrImageFromDirectory(const std::string& path);

/** Abstract interface for HDR provider. */
class IHdrProvider
{
public:
    virtual ~IHdrProvider() = default;

    /** HDR acquisition mode. */
    virtual HdrAcquisitionMode Mode() const = 0;

    /** Returns if the HDR provider is supported for the current camera. */
    virtual bool IsSupported() const = 0;

    /** Configures the HDR provider with the given exposure sequence. */
    virtual void Configure(const ExposureSequence& exposures_s) = 0; // NOLINT(readability-identifier-naming)

    /** Acquires the image sequence and calculates the HDR result. */
    virtual HdrResult AcquireHdrImage() = 0;

    /** Acquires the HDR image sequence. */
    virtual ImageSequence AcquireHdrSequence() = 0;
};

/**
 * Implements progressive HDR by capturing a sequence of
 * software-triggered images, adjusting the exposure time for each
 * capture programmatically.
 */
class ProgressiveHdrProvider : public IHdrProvider
{
public:
    explicit ProgressiveHdrProvider(const std::shared_ptr<Camera>& camera);

    /** HDR acquisition mode. */
    HdrAcquisitionMode Mode() const override;

    /** Returns if the HDR provider is supported for the current camera. */
    bool IsSupported() const override;

    /** Configures the HDR provider with the given exposure sequence. */
    void Configure(const ExposureSequence& exposureSequence_s) override; // NOLINT(readability-identifier-naming)

    /** Captures the image sequence once and calculates the HDR image. */
    HdrResult AcquireHdrImage() override;

    /** Acquires the HDR image sequence. */
    ImageSequence AcquireHdrSequence() override;

private:
    std::shared_ptr<Camera> m_camera{};
    ExposureSequence m_deviceExposureSequence_s{};
};

/**
 * Implements HDR by capturing a predefined exposure sequence
 * using the camera’s sequencer feature.
 */
class SequencerHdrProvider : public IHdrProvider
{
public:
    explicit SequencerHdrProvider(const std::shared_ptr<Camera>& camera);

    /** HDR acquisition mode. */
    HdrAcquisitionMode Mode() const override;

    /** Returns if the HDR provider is supported for the current camera. */
    bool IsSupported() const override;

    /** Configures the HDR provider with the given exposure sequence. */
    void Configure(const ExposureSequence& exposureSequence_s) override; // NOLINT(readability-identifier-naming)

    /** Captures the image sequence once and calculates the HDR image. */
    HdrResult AcquireHdrImage() override;

    /** Acquires the HDR image sequence. */
    ImageSequence AcquireHdrSequence() override;

private:
    /** Check if the HDR mode is supported for the current camera. */
    bool CheckHdrSupported() const;

    std::shared_ptr<Camera> m_camera{};

    bool m_supported{};
    ExposureSequence m_deviceExposureSequence_s{};
};

/**
 * HDR implementation for cameras with QuadHDR sensor support.
 */
class QuadExposureHdrProvider : public IHdrProvider
{
public:
    explicit QuadExposureHdrProvider(const std::shared_ptr<Camera>& camera);

    /** HDR acquisition mode. */
    HdrAcquisitionMode Mode() const override;

    /** Returns if the HDR provider is supported for the current camera. */
    bool IsSupported() const override;

    /** Configures the HDR provider with the given exposure sequence. */
    void Configure(const ExposureSequence& exposureSequence_s) override; // NOLINT(readability-identifier-naming)

    /** Captures the image sequence once and calculates the HDR image. */
    HdrResult AcquireHdrImage() override;

    /** Acquires the HDR image sequence. */
    ImageSequence AcquireHdrSequence() override;

private:
    /** Check if the HDR mode is supported for the current camera. */
    bool CheckHdrSupported() const;

    std::shared_ptr<Camera> m_camera{};
    ExposureSequence m_deviceExposureSequence_s{};

    bool m_supported{};
};

/**
 * HDR implementation for cameras with ClearHDR sensor support.
 */
class ClearHdrProvider : public IHdrProvider
{
public:
    explicit ClearHdrProvider(const std::shared_ptr<Camera>& camera);

    /** HDR acquisition mode. */
    HdrAcquisitionMode Mode() const override;

    /** Returns if the HDR provider is supported for the current camera. */
    bool IsSupported() const override;

    /** Configures the HDR provider with the given exposure sequence. */
    void Configure(const ExposureSequence& exposureSequence_s) override; // NOLINT(readability-identifier-naming)

    /** Captures the image sequence once and calculates the HDR image. */
    HdrResult AcquireHdrImage() override;

    /** Acquires the HDR image sequence. */
    ImageSequence AcquireHdrSequence() override;

private:
    /** Check if the HDR mode is supported for the current camera. */
    bool CheckHdrSupported() const;

    std::shared_ptr<Camera> m_camera{};
    bool m_supported{};

    double m_deviceExposure_s{};
    std::vector<double> m_deviceGains{};
};

/**
 * Resolves and manages HDR providers for a given camera.
 */
class HdrProviderRegistry
{
public:
    explicit HdrProviderRegistry(const std::shared_ptr<Camera>& camera);

    /** All registered HDR providers, ordered by preference. */
    const std::vector<std::shared_ptr<IHdrProvider>>& Providers() const;

    /**
     * \brief Return the supported HDR provider for the given acquisition mode.
     *
     * @throw std::runtime_error  If no supported provider exists for the given mode.
     */
    std::shared_ptr<IHdrProvider> GetProvider(HdrAcquisitionMode hdrAcquisitionMode) const;

    /**
     * \brief Return the most preferred supported HDR provider.
     *
     * @throw std::runtime_error  If no supported HDR provider is available.
     */
    std::shared_ptr<IHdrProvider> PreferredProvider() const;

private:
    std::vector<std::shared_ptr<IHdrProvider>> m_providers{};
};
} // namespace hdr
