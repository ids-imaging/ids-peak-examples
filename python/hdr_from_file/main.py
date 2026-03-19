# Copyright (C) 2026, IDS Imaging Development Systems GmbH.
#
# Permission to use, copy, modify, and/or distribute this software for
# any purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
# FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
# AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.


import os
import sys
from typing import List

import numpy as np

from ids_peak_common import Metadata, MetadataKey

from ids_peak_icv import Image, ICVException
from ids_peak_icv.experimental.hdr import HDR, ToneMapping
from ids_peak_icv.experimental.hdr.hdr import ImageArray

# --------------------------------------------------------------------------------------------------
# UTILITIES
# --------------------------------------------------------------------------------------------------

def exposure_to_string(exposure: float) -> str:
    return "{:.3f}".format(exposure).replace(".", "_")


def read_images_from_dir(directory_path: str, exposure_times: List[float]) -> ImageArray:
    images = []

    for exposure_time in exposure_times:
        filename = "image_{}_ms.png".format(exposure_to_string(exposure_time / 1000))
        file_path = os.path.join(directory_path, filename)

        image = Image.create_from_file(file_path)

        images.append(image)

    return np.array(images)


def set_exposure_metadata(images: ImageArray, exposure_times: List[float]) -> None:
    for image, exposure_time in zip(images, exposure_times, strict=True):
        metadata = Metadata()
        metadata.set_value_by_key(MetadataKey.DEVICE_EXPOSURE_TIME, exposure_time)
        image.metadata = metadata


def get_calibration_exposures_microseconds() -> List[float]:
    return [502., 803., 1296., 2085., 3353., 5400., 8685., 13982., 22501.]

def get_process_exposures_microseconds() -> List[float]:
    return [502., 1296., 3353., 8685., 22501.]

def read_calibration_images_from_dir(directory_path: str) -> ImageArray:
    return read_images_from_dir(directory_path, get_calibration_exposures_microseconds())


def read_processing_images_from_dir(directory_path: str) -> ImageArray:
    return read_images_from_dir(directory_path, get_process_exposures_microseconds())


def get_output_file_path(prefix: str, extension: str) -> str:
    return "{}.{}".format(prefix, extension)


# --------------------------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------------------------

def main() -> None:
    try:
        script_path = os.path.dirname(os.path.realpath(__file__))
        data_path = os.path.join(script_path, "../../data/hdr_from_file")

        calibration_images_path = os.path.join(data_path, "calibration")
        processing_images_path = os.path.join(data_path, "processing")

        print("Initialize HDR")
        hdr = HDR()

        print("Loading calibration images from", calibration_images_path)
        calibration_images = read_calibration_images_from_dir(calibration_images_path)

        # It is important to set the exposure time of the images to the images metadata
        set_exposure_metadata(calibration_images, get_calibration_exposures_microseconds())

        print("Estimate camera response curve")
        hdr.estimate_response_curve(calibration_images)

        print("Loading processing images from", processing_images_path)
        processing_images = read_processing_images_from_dir(processing_images_path)

        # It is important to set the exposure time of the images to the images metadata
        set_exposure_metadata(processing_images, get_process_exposures_microseconds())

        # It is also possible to skip the calibrate method,
        # then calibration is done on first call of process method
        print("Process HDR image")
        hdr_image = hdr.process(processing_images)

        hdr_output_path = "hdr_image.tiff"
        hdr_image.save(hdr_output_path)
        print("HDR image saved to", hdr_output_path)

        print("Initialize tone mapping")
        tone_mapping = ToneMapping()

        print("Tone mapping of HDR image")
        ldr_image = tone_mapping.process(hdr_image)

        ldr_output_path = "tone_mapped_ldr_image.png"
        ldr_image.save(ldr_output_path)
        print("Tone mapped ldr image saved to", ldr_output_path)

    except ICVException as e:
        print(e)
        sys.exit(e.status.value)
    except Exception as e:
        print(e)
        sys.exit(-1)


if __name__ == "__main__":
    main()
