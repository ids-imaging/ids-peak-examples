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

#include <iomanip>
#include <iostream>
#include <string>

#include <peak_icv/peak_icv.hpp>

#ifndef DATA_PATH
#    error "Define DATA_PATH to the examples data folder"
#endif

namespace
{
std::vector<peak::icv::Image> ReadImagesFromDir(const std::string& directoryPath);
} // namespace

int main()
{
    try
    {
        peak::icv::library::Init();

        constexpr auto inputImagesPath = DATA_PATH "/calibration_from_file";
        std::cout << "Loading images from " << inputImagesPath << std::endl;
        const auto inputImages = ReadImagesFromDir(inputImagesPath);

        std::cout << "Initialize calibration" << std::endl;
        const peak::icv::CalibrationPlate calibrationPlate(
            DATA_PATH "/calibration_from_file/1012041-radon-checkerboard-marker-65mm-6x6.json");
        const peak::icv::CameraCalibration calibration(calibrationPlate);

        std::cout << "Process calibration" << std::endl;
        const auto calibrationResult = calibration.Process(inputImages);

        const auto meanReprojectionError = calibrationResult.GetMeanReprojectionError();
        std::cout << "Calibration finished with mean reprojection error: " << meanReprojectionError << std::endl;

        constexpr auto outputFilePath = "calibration_result.json";
        const peak::icv::CalibrationResultWriter writer;
        writer.Write(outputFilePath, calibrationResult);
        std::cout << "Calibration result saved to file to " << outputFilePath << std::endl;

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

std::vector<peak::icv::Image> ReadImagesFromDir(const std::string& directoryPath)
{
    constexpr auto numImages = 16;
    std::vector<peak::icv::Image> images;

    for (int i = 0; i < numImages; ++i)
    {
        std::stringstream ss;
        ss << directoryPath << "/image_" << std::setw(2) << std::setfill('0') << i + 1 << ".png";

        images.emplace_back(ss.str());
    }

    return images;
}
} // namespace
