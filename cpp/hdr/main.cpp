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
#include "hdr.hpp"
#include "save_hdr_image.hpp"
#include "utils.hpp"

#include <peak/peak.hpp>
#include <peak_common/peak_common.hpp>
#include <peak_icv/peak_icv.hpp>

#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace hdr;

namespace
{
struct AppArgs
{
    bool showHelp{ false };
    IntervalD exposureRange_s{ 0.0005, 0.05 };
    std::string serialNumber;
    std::string outputDirectory;
    std::string inputDirectory;
    size_t numExposures{ 4 };
    HdrAcquisitionMode hdrAcquisitionMode{ HdrAcquisitionMode::Auto };
};

AppArgs ParseArgs(const std::vector<std::string>& args);
std::string CreateFileName(size_t index, double exposureTime_ms); // NOLINT(readability-identifier-naming)
void SaveHdrResult(const std::string& path, const HdrResult& result);
void ProcessSavedImages(const AppArgs& args);

void PrintHelp(const char* progName);
void PrintSupportedAcquisitionModes(const HdrProviderRegistry& registry);
void PrintExposureSequence(const ExposureSequence& exposures);
} // namespace

int main(int argc, char* argv[])
{
    try
    {
        const auto& args = ParseArgs({ argv, argv + argc });

        if (args.showHelp)
        {
            PrintHelp(argv[0]);
            return EXIT_SUCCESS;
        }

        std::cout << "Initializing library..." << "\n";
        utils::ICVLibraryGuard icvGuard(std::cerr);

        // If input directory is specified, process saved images and exit
        if (!args.inputDirectory.empty())
        {
            ProcessSavedImages(args);
            return EXIT_SUCCESS;
        }

        utils::APILibraryGuard apiGuard(std::cerr);

        // 1. Open device and reset to default
        std::shared_ptr<Camera> camera{};
        if (args.serialNumber.empty())
        {
            camera = std::make_shared<Camera>(Camera::OpenFirstAvailable());
        }
        else
        {
            camera = std::make_shared<Camera>(Camera::OpenBySerialNumber(args.serialNumber));
        }

        camera->ResetToDefault();

        // 2. Find which HDR option is available
        const HdrProviderRegistry registry(camera);
        PrintSupportedAcquisitionModes(registry);

        // 3. Configure HDR option
        std::shared_ptr<IHdrProvider> provider{};
        if (args.hdrAcquisitionMode == HdrAcquisitionMode::Auto)
        {
            provider = registry.PreferredProvider();
        }
        else
        {
            provider = registry.GetProvider(args.hdrAcquisitionMode);
            if (!provider->IsSupported())
            {
                std::ostringstream oss;
                oss << "Acquisition mode " << args.hdrAcquisitionMode << " is not supported by this device.";
                throw std::runtime_error(oss.str());
            }
        }

        std::cout << "Using mode " << provider->Mode() << " for HDR image acquisition."
                  << "\n";

        // 4. Capture image sequence
        const auto& exposureSequence = CreateExposureSequence(args.exposureRange_s, args.numExposures);
        provider->Configure(exposureSequence);

        PrintExposureSequence(exposureSequence);

        const auto start = std::chrono::steady_clock::now();
        const auto hdrCaptureResult = provider->AcquireHdrImage();
        const auto end = std::chrono::steady_clock::now();
        std::cout << "Capture took " << std::chrono::duration_cast<std::chrono::milliseconds>(end - start).count()
                  << " ms" << "\n";

        // (5.) Save images to disk
        if (!args.outputDirectory.empty())
        {
            SaveHdrResult(args.outputDirectory, hdrCaptureResult);
        }

        camera->ResetToDefault();
    }
    catch (const std::exception& e)
    {
        std::cerr << "Error: " << e.what() << "\n";
        return EXIT_FAILURE;
    }
}

namespace
{

AppArgs ParseArgs(const std::vector<std::string>& args)
{
    AppArgs result{};
    std::pair<double, double> exposureRange{ 0.0, 0.0 };

    for (size_t i = 1; i < args.size(); ++i)
    {
        const std::string& arg = args.at(i);

        std::string key;
        std::string val;
        std::tie(key, val) = utils::SplitArg(arg);

        auto getValue = [&] {
            if (!val.empty())
            {
                return val;
            }
            if (i + 1 < args.size())
            {
                return std::string(args.at(++i));
            }
            throw std::runtime_error("Missing value for " + key);
        };


        if (key == "-h" || key == "--help")
        {
            result.showHelp = true;
        }
        else if (key == "--min")
        {
            exposureRange.first = std::stof(getValue()) / 1000.0;
        }
        else if (key == "--max")
        {
            exposureRange.second = std::stof(getValue()) / 1000.0;
        }
        else if (key == "-n" || key == "--num-exposures")
        {
            result.numExposures = std::stoul(getValue());
        }
        else if (key == "-s" || key == "--serial")
        {
            result.serialNumber = getValue();
        }
        else if (key == "-o" || key == "--out-dir")
        {
            result.outputDirectory = getValue();
        }
        else if (key == "-i" || key == "--in-dir")
        {
            result.inputDirectory = getValue();
        }
        else if (key == "-a" || key == "--acquisition-mode")
        {
            result.hdrAcquisitionMode = StringToHdrAcquisitionMode(getValue());
        }
    }

    if (exposureRange.first > 0 && exposureRange.second > 0)
    {
        result.exposureRange_s = { exposureRange.first, exposureRange.second };
    }
    if ((exposureRange.first > 0) != (exposureRange.second > 0))
    {
        throw std::invalid_argument("You must provide both --min and --max, or neither.");
    }

    return result;
}

std::string CreateFileName(size_t index, double exposureTime_ms) // NOLINT(readability-identifier-naming)
{
    std::stringstream ss;
    ss << "seq" << index << "_" << std::fixed << std::setprecision(3) << exposureTime_ms << ".png";
    std::string filename = ss.str();
    const size_t dotPos = filename.find('.');
    if (dotPos != std::string::npos)
    {
        filename.replace(dotPos, 1, "ms");
    }

    return filename;
}

void SaveHdrResult(const std::string& path, const HdrResult& result)
{
    utils::EnsurePathExists(path);

    constexpr peak::icv::ImageWriter writer;
    for (size_t i = 0; i < result.imageSequence.size(); ++i)
    {
        const auto metadata = result.imageSequence.at(i).GetMetadata();
        auto exposureTime_ms = // NOLINT(readability-identifier-naming)
            metadata.GetValueByKey<peak::common::MetadataKey::DeviceExposureTime>() / 1000.0;
        if (metadata.HasEntryByKey<peak::common::MetadataKey::DeviceGain>())
        {
            exposureTime_ms *= metadata.GetValueByKey<peak::common::MetadataKey::DeviceGain>();
        }

        const auto& filename = CreateFileName(i, exposureTime_ms);

        const std::string filePath = utils::JoinPath(path, filename);

        writer.Write(filePath, result.imageSequence.at(i));
        std::cout << "Saving sequence image to " << filePath << '\n';
    }

    const std::string hdrPreviewImagePath = path + "/" + "hdr_preview_8bit.png";
    writer.Write(hdrPreviewImagePath, result.ldrImage);
    std::cout << "Saving hdr preview image to " << hdrPreviewImagePath << '\n';

    const std::string hdrImagePathTiff = path + "/" + "hdr_image.tiff";
    writer.Write(hdrImagePathTiff, result.hdrImage);
    std::cout << "Saving hdr image to " << hdrImagePathTiff << "\n";

    const std::string hdrImagePathHdr = path + "/" + "hdr_image.hdr";
    utils::SaveHdrImage(result.hdrImage, hdrImagePathHdr);
    std::cout << "Saving hdr image to " << hdrImagePathHdr << "\n";
}

void ProcessSavedImages(const AppArgs& args)
{
    // Load images from disk and create HDR image
    const auto result = CalculateHdrImageFromDirectory(args.inputDirectory);

    // Save images to disk if output directory specified
    if (!args.outputDirectory.empty())
    {
        SaveHdrResult(args.outputDirectory, result);
    }
}

void PrintHelp(const char* progName)
{
    const auto hdrAcquisitionModes = utils::JoinToString(
        std::vector<HdrAcquisitionMode>{ HdrAcquisitionMode::Auto, HdrAcquisitionMode::Sequencer,
            HdrAcquisitionMode::Progressive, HdrAcquisitionMode::QuadExposure, HdrAcquisitionMode::ClearHdr });

    std::cout << "Usage: " << progName << " [options]\n"
              << "Options:\n"
              << "  -h, --help                      Show this information\n"
              << "  --min <val>                     Minimum exposure value in milliseconds\n"
              << "  --max <val>                     Maximum exposure value in milliseconds\n"
              << "  -n, --num-exposures <num>       Number of exposures (default: 5)\n"
              << "  -s, --serial <serial>           Serial number of camera\n"
              << "  -o, --out-dir <dir>             Output directory\n"
              << "  -i, --in-dir <dir>              Input directory (not fully implemented in C++ example)\n"
              << "  -a, --acquisition-mode <mode>   Mode used to capture the image sequence. (" << hdrAcquisitionModes
              << ")\n";
}

void PrintSupportedAcquisitionModes(const HdrProviderRegistry& registry)
{
    std::cout << "Available HDR image acquisition modes: ";
    std::unordered_set<HdrAcquisitionMode> supportedAcquisitionModes{};
    for (const auto& provider : registry.Providers())
    {
        if (provider->IsSupported())
        {
            supportedAcquisitionModes.emplace(provider->Mode());
        }
    }
    std::cout << utils::JoinToString(supportedAcquisitionModes) << "\n";
}

void PrintExposureSequence(const ExposureSequence& exposures)
{
    std::cout << "Capturing " << exposures.size() << " images" << "\n";
    std::cout << "  - Exposures: ";
    for (size_t i = 0; i < exposures.size(); ++i)
    {
        std::cout << std::fixed << std::setprecision(3) << exposures.at(i) * 1'000 << "ms";
        if (i < exposures.size() - 1)
        {
            std::cout << ", ";
        }
    }
    std::cout << "\n";
}

} // namespace
