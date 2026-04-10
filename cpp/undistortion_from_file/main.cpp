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

#ifndef DATA_PATH
#    error "Define DATA_PATH to the examples data folder"
#endif

int main()
{
    try
    {
        peak::icv::library::Init();

        constexpr auto inputImagePath = DATA_PATH "/undistortion_from_file/fisheye.png";
        std::cout << "Loading input image from " << inputImagePath << std::endl;
        const peak::icv::Image inputImage(inputImagePath);

        constexpr auto calibrationParametersPath = DATA_PATH "/undistortion_from_file/calibration_parameters.json";
        std::cout << "Loading intrinsic parameters from " << calibrationParametersPath << std::endl;
        const peak::icv::CalibrationParameters calibrationParameters(calibrationParametersPath);

        std::cout << "Initialize undistortion" << std::endl;
        peak::icv::Undistortion undistortion(calibrationParameters.GetIntrinsicParameters());

        std::cout << "Process undistortion" << std::endl;
        const peak::icv::UndistortedImage outputImage = undistortion.Process(inputImage);

        peak::icv::ImageWriter writer;
        writer.Write("undistorted_image.png", outputImage);
        std::cout << "Undistorted image saved" << std::endl;

        peak::icv::library::Exit();
    }
    catch (const std::exception& e)
    {
        std::cout << e.what() << std::endl;
        return 1;
    }
    return 0;
}
