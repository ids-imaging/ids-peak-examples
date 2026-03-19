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

// ---------------------------------------------------------------------------------------------------------------------
// DECLARATIONS
// ---------------------------------------------------------------------------------------------------------------------

namespace
{
std::vector<uint32_t> GetExposureTimesCalibrationMicroSeconds();
std::vector<uint32_t> GetExposureTimesProcessMicroSeconds();
std::string GetCalibrationImageFilePath();
std::string GetProcessingImageFilePath();
std::string GetToneMappedLdrImageFilePath();
std::string GetHdrImageFilePath();
std::vector<peak::icv::Image> ReadImagesFromDir(
    const std::string& directoryPath, const std::vector<uint32_t>& exposureTimes);
void SetImagesExposureMetaData(std::vector<peak::icv::Image>& images, const std::vector<uint32_t>& exposureTimes);
std::vector<peak::icv::Image> ReadCalibrationImagesFromDir(const std::string& directoryPath);
std::vector<peak::icv::Image> ReadProcessingImagesFromDir(const std::string& directoryPath);
} // namespace

// ---------------------------------------------------------------------------------------------------------------------
// MAIN
// ---------------------------------------------------------------------------------------------------------------------

int main()
{
    try
    {
        peak::icv::library::Init();

        const peak::icv::ImageWriter writer;

        std::cout << "Initialize HDR" << std::endl;
        peak::icv::experimental::HDR hdr;

        std::cout << "Loading calibration images from " << GetCalibrationImageFilePath() << std::endl;
        auto calibrationImages = ReadCalibrationImagesFromDir(GetCalibrationImageFilePath());

        // It is important to set the exposure time of the images to the images metadata
        SetImagesExposureMetaData(calibrationImages, GetExposureTimesCalibrationMicroSeconds());

        std::cout << "Estimate camera response curve" << std::endl;
        hdr.EstimateResponseCurve(calibrationImages);

        std::cout << "Loading processing images from " << GetProcessingImageFilePath() << std::endl;
        auto processingImages = ReadProcessingImagesFromDir(GetProcessingImageFilePath());

        // It is important to set the exposure time of the images to the images metadata
        SetImagesExposureMetaData(processingImages, GetExposureTimesProcessMicroSeconds());

        // It is also possible to skip the Calibrate method, then calibration is done on first call of Process method
        std::cout << "Process HDR image" << std::endl;
        const auto hdrImage = hdr.Process(processingImages);

        writer.Write(GetHdrImageFilePath(), hdrImage);
        std::cout << "HDR image saved to " << GetHdrImageFilePath() << std::endl;

        std::cout << "Initialize tone mapping" << std::endl;
        peak::icv::experimental::ToneMapping toneMapping;

        std::cout << "Tone mapping of HDR image" << std::endl;
        const auto ldrImage = toneMapping.Process(hdrImage);

        writer.Write(GetToneMappedLdrImageFilePath(), ldrImage);
        std::cout << "Tone mapped ldr image saved to " << GetToneMappedLdrImageFilePath() << std::endl;

        peak::icv::library::Exit();
    }
    catch (const std::exception& e)
    {
        std::cout << e.what() << std::endl;
        return 1;
    }
    return 0;
}

// ---------------------------------------------------------------------------------------------------------------------
// INPUT/OUTPUT UTILITIES
// ---------------------------------------------------------------------------------------------------------------------

namespace
{

std::vector<uint32_t> GetExposureTimesCalibrationMicroSeconds()
{
    return { 502, 803, 1'296, 2'085, 3'353, 5'400, 8'685, 13'982, 22'501 };
}

std::vector<uint32_t> GetExposureTimesProcessMicroSeconds()
{
    return { 502, 1'296, 3'353, 8'685, 22'501 };
}

#ifndef DATA_PATH
#    error "Define DATA_PATH to the examples data folder"
#endif

std::string GetCalibrationImageFilePath()
{
    return DATA_PATH + std::string("/hdr_from_file/calibration");
}

std::string GetProcessingImageFilePath()
{
    return DATA_PATH + std::string("/hdr_from_file/processing");
}

std::string GetToneMappedLdrImageFilePath()
{
    return "tone_mapped_ldr_image.png";
}

std::string GetHdrImageFilePath()
{
    return "hdr_image.tiff";
}

std::string ExposureToString(const double exposure)
{
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(3) << exposure;
    std::string s = ss.str();

    for (char& c : s)
    {
        if (c == '.')
        {
            c = '_';
        }
    }

    return s;
}

std::vector<peak::icv::Image> ReadImagesFromDir(
    const std::string& directoryPath, const std::vector<uint32_t>& exposureTimes)
{
    std::vector<peak::icv::Image> images;
    images.reserve(exposureTimes.size());

    for (double exposureTime : exposureTimes)
    {
        const auto filePath = directoryPath + "/image_" + ExposureToString(exposureTime / 1'000) + "_ms.png";
        images.emplace_back(filePath);
    }

    return images;
}

void SetImagesExposureMetaData(std::vector<peak::icv::Image>& images, const std::vector<uint32_t>& exposureTimes)
{
    for (size_t i = 0; i < exposureTimes.size(); ++i)
    {
        peak::common::Metadata metaData;
        metaData.SetValueByKey<peak::common::MetadataKey::DeviceExposureTime>(exposureTimes[i]);
        images[i].SetMetadata(metaData);
    }
}

std::vector<peak::icv::Image> ReadCalibrationImagesFromDir(const std::string& directoryPath)
{
    return ReadImagesFromDir(directoryPath, GetExposureTimesCalibrationMicroSeconds());
}

std::vector<peak::icv::Image> ReadProcessingImagesFromDir(const std::string& directoryPath)
{
    return ReadImagesFromDir(directoryPath, GetExposureTimesProcessMicroSeconds());
}
} // namespace
