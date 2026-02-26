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

#include <peak_common/types/peak_common_pixel_format.hpp>
#include <peak_icv/types/peak_icv_image.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <ios>
#include <iosfwd>

namespace utils
{
struct FloatPixel
{
    float r;
    float g;
    float b;
};

static_assert(sizeof(FloatPixel) == sizeof(float) * 3, "FloatPixel must contain exactly 3 floats");

inline std::array<uint8_t, 4> RgbFloat2Rgbe(const FloatPixel& pixel)
{
    auto maxVal = std::max({ pixel.r, pixel.g, pixel.b });
    if (maxVal < 1e-32)
    {
        return {};
    }

    int e;
    const auto m = std::frexp(maxVal, &e);
    const auto scale = m * 256.0F / maxVal;

    std::array<uint8_t, 4> rgbe{};
    rgbe[0] = static_cast<uint8_t>(pixel.r * scale);
    rgbe[1] = static_cast<uint8_t>(pixel.g * scale);
    rgbe[2] = static_cast<uint8_t>(pixel.b * scale);
    rgbe[3] = static_cast<uint8_t>(e + 128);

    return rgbe;
}

inline std::array<uint8_t, 4> MonoFloat2Rgbe(const float& pixel)
{
    if (pixel < 1e-32)
    {
        return {};
    }

    int e;
    std::array<uint8_t, 4> rgbe{};
    {
        const auto value = static_cast<uint8_t>(std::frexp(pixel, &e) * 256.0F);
        rgbe[0] = value;
        rgbe[1] = value;
        rgbe[2] = value;
        rgbe[3] = static_cast<uint8_t>(e + 128);
    }
    return rgbe;
}

inline void SaveHdrImage(const peak::icv::Image& image, const std::string& filename)
{
    if (image.GetPixelFormat() != peak::common::PixelFormat::RGB32fIDS
        && image.GetPixelFormat() != peak::common::PixelFormat::Mono32fIDS)
    {
        throw std::runtime_error("Failed to save HDR image: the given image has no HDR pixel format!");
    }

    std::ofstream file(filename, std::ios::binary);
    if (!file)
    {
        throw std::runtime_error("Failed to open file for writing!");
    }

    // Radiance HDR header
    file << "#?RADIANCE\n";
    // Note: we state rle compression though it is not. OpenHDR seems to have a bug and otherwise will fail.
    file << "FORMAT=32-bit_rle_rgbe\n\n";
    file << "-Y " << image.GetSize().GetHeight() << " +X " << image.GetSize().GetWidth() << "\n";

    if (image.GetPixelFormat() == peak::common::PixelFormat::RGB32fIDS)
    {
        const auto* pixels = reinterpret_cast<const FloatPixel*>(image.GetData());
        const size_t pixelCount = image.GetSizeInBytes() / sizeof(FloatPixel);

        for (size_t i = 0; i < pixelCount; ++i)
        {
            auto rgbe = RgbFloat2Rgbe(pixels[i]);
            file.write(reinterpret_cast<const char*>(rgbe.data()), 4);
        }
    }
    else
    {
        const auto* pixels = reinterpret_cast<const float*>(image.GetData());
        const size_t pixelCount = image.GetSizeInBytes() / sizeof(float);

        for (size_t i = 0; i < pixelCount; ++i)
        {
            auto rgbe = MonoFloat2Rgbe(pixels[i]);
            file.write(reinterpret_cast<const char*>(rgbe.data()), 4);
        }
    }
}
} // namespace utils
