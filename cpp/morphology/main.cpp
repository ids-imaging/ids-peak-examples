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

#include <peak_common/peak_common.hpp>
#include <peak_icv/peak_icv.hpp>
#include <iostream>

namespace
{
peak::icv::Region CreateRegion();
peak::icv::Image CreateCheckerImage(const peak::common::Size& size);
void WriteRegionToImageFile(const peak::icv::Region& region, const std::string& outputFilename);
} // namespace

int main()
{
    try
    {
        peak::icv::library::Init();

        auto region = CreateRegion();
        WriteRegionToImageFile(region, "region.png");

        peak::icv::Region structuringElement{
            peak::common::Rectangle{ { -1, -1 }, { 3, 3 } }
        };

        // Apply Dilation
        auto regionDilated = region.Dilation(structuringElement);
        WriteRegionToImageFile(regionDilated, "region_dilated.png");

        // Apply Erosion
        auto regionEroded = region.Erosion(structuringElement);
        WriteRegionToImageFile(regionEroded, "region_eroded.png");

        peak::icv::library::Exit();
    }
    catch (const std::exception& e)
    {
        std::cout << e.what() << std::endl;
        return 1;
    }
    return 0;
}

namespace
{
peak::icv::Region CreateRegion()
{
    peak::icv::Region region{
        {
         { 2, 2 },
         { 3, 2 },
         { 4, 2 },
         { 2, 3 },
         { 3, 3 },
         { 4, 3 },
         { 2, 4 },
         { 3, 4 },
         { 4, 4 },
         { 5, 4 },
         { 3, 5 },
         }
    };
    return region;
}

peak::icv::Image CreateCheckerImage(const peak::common::Size& size)
{
    peak::icv::Image image{ peak::common::PixelFormat::RGB8, size };
    auto* data = image.GetData();
    auto imageWidth = static_cast<size_t>(image.GetSize().GetWidth());
    auto imageHeight = static_cast<size_t>(image.GetSize().GetHeight());
    for (size_t r = 0; r < imageHeight; ++r)
    {
        for (size_t c = 0; c < imageWidth; ++c)
        {
            uint8_t val{ 205 };
            if (((r + c) % 2) != 0)
            {
                val = 50;
            }
            auto pel = (r * imageWidth + c) * 3;
            data[pel] = val;
            data[pel + 1] = val;
            data[pel + 2] = val;
        }
    }
    return image;
}

void WriteRegionToImageFile(const peak::icv::Region& region, const std::string& outputFilename)
{
    peak::icv::Image rgbImage = CreateCheckerImage({ 8, 8 });
    peak::icv::Painter painter{ rgbImage };
    painter.Draw(region);

    peak::icv::ImageWriter writer;
    writer.Write(outputFilename, rgbImage);
}
} // namespace
