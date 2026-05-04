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

#include <iostream>
#include <string>

#include <peak_icv/peak_icv.hpp>

namespace
{
void SaveResultToFile(
    const peak::icv::Image& inputImage, const peak::icv::Region& region, const std::string& imageFileName);
} // namespace

int main()
{
    try
    {
        peak::icv::library::Init();

        constexpr auto imageFilePath = DATA_PATH "/image_region_from_file/beads.png";
        std::cout << "Loading image " << imageFilePath << "." << std::endl;
        const peak::icv::Image inputImage(imageFilePath);

        peak::common::Rectangle minuendRect{
            peak::common::Point{ 130,  80 },
            peak::common::Size{ 110, 150 }
        };
        peak::common::Rectangle subtrahendRect{
            peak::common::Point{ 157, 117 },
            peak::common::Size{  55,  75 }
        };
        // compute the difference of the two regions to have a rectangular region, but with an empty space inside
        const auto region = peak::icv::Region(minuendRect).Difference(peak::icv::Region(subtrahendRect));

        std::cout << "Set a region for the image." << std::endl;
        inputImage.SetRegion(region);

        std::cout << "Applying a threshold on the reduced image region." << std::endl;
        peak::icv::Threshold threshold{ 25, 255 };
        auto thresholdRegion = threshold.Process(inputImage);

        SaveResultToFile(inputImage, thresholdRegion, "image_reduced_region.png");

        std::cout << "Reset image region to full image size." << std::endl;
        inputImage.ResetRegion();

        thresholdRegion = threshold.Process(inputImage);
        SaveResultToFile(inputImage, thresholdRegion, "image_full_region.png");

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
void SaveResultToFile(
    const peak::icv::Image& inputImage, const peak::icv::Region& region, const std::string& imageFileName)
{
    // For the painter an 8-bit color image is needed
    auto rgbImage = inputImage.ConvertPixelFormat(peak::common::PixelFormat::RGB8);

    peak::icv::Painter painter(rgbImage);

    std::cout << "Painting the used image region in green." << std::endl;
    painter.SetOpacity(peak::icv::Opacity(25));
    painter.SetColor(peak::icv::Color(0, 255, 0));
    const auto imageRegion = inputImage.GetRegion();
    painter.Draw(imageRegion);

    std::cout << "Painting threshold result in red." << std::endl;
    painter.SetOpacity(peak::icv::Opacity(100));
    painter.SetColor(peak::icv::Color(255, 0, 0));
    painter.Draw(region);

    peak::icv::ImageWriter writer;
    writer.Write(imageFileName, rgbImage);
    std::cout << "Saved image to " << imageFileName << "." << std::endl;
}
} // namespace
