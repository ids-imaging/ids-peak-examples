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

import numpy as np

from ids_peak_icv import Image, ICVException
from ids_peak_icv.calibration import CalibrationPlate, CameraCalibration
from ids_peak_icv.calibration.camera_calibration import ImageArray


def main() -> None:
    try:
        script_path = os.path.dirname(os.path.realpath(__file__))
        data_path = os.path.join(script_path, "../../data/calibration_from_file")
        calibration_plate_path = os.path.join(data_path,
                                              "1012041-radon-checkerboard-marker-65mm-6x6.json")

        print("Loading images from", data_path)
        images = load_images_from_directory(data_path)

        print("Initialize calibration")
        calibration_plate = CalibrationPlate.create_from_file(calibration_plate_path)
        camera_calibration = CameraCalibration.create_from_plate(calibration_plate)

        print("Process calibration")
        result = camera_calibration.process(images)
        print("Calibration finished with mean reprojection error:", result.mean_reprojection_error)

        output_file_path =  "calibration_result.json"

        result.save(output_file_path)
        print("Calibration result saved to file to", output_file_path)
    except ICVException as e:
        print(e)
        sys.exit(e.status.value)
    except Exception as e:
        print(e)
        sys.exit(-1)


def load_images_from_directory(path: str) -> ImageArray:
    images = []
    # Sorting the images is recommended, as the order of the extrinsic
    # parameters depends on the order of the images
    for f in sorted(os.listdir(path)):
        if f.endswith(".png"):
            images.append(Image.create_from_file(os.path.join(path, f)))
    return np.array(images)


if __name__ == "__main__":
    main()
