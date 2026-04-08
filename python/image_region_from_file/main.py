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

from ids_peak_common import PixelFormat, Rectangle, Interval
from ids_peak_icv import Image, Region, ICVException
from ids_peak_icv.thresholds import Threshold
from ids_peak_icv.painting import Painter, Opacity, Color


def main() -> None:
    try:
        # load image
        script_path = os.path.dirname(os.path.realpath(__file__))
        image = Image.create_from_file(os.path.join(script_path,
                                                    "../../data/image_region_from_file/beads.png"))

        # convert to grayscale
        image_gray = image.convert_pixel_format(PixelFormat.MONO_8)

        # create rectangular image region
        region_minuend = Region.create_from_rectangle(
            Rectangle.create_from_coordinates_and_dimensions(130, 80, 110, 150))
        region_subtrahend = Region.create_from_rectangle(
            Rectangle.create_from_coordinates_and_dimensions(157, 117, 55, 75))
        region = region_minuend.difference(region_subtrahend)
        image_gray.region = region

        # apply threshold
        print("Applying a threshold on the reduced image region.")
        threshold = Threshold(Interval(25, 255))
        threshold_region = threshold.process(image_gray)
        save_result_to_file(image_gray, threshold_region, "image_reduced_region.png")

        print("Reset image region to full image size.")
        image_gray.reset_region()
        threshold_region = threshold.process(image_gray)
        save_result_to_file(image_gray, threshold_region, "image_full_region.png")


    except ICVException as e:
        print(e)
        sys.exit(e.status.value)
    except Exception as e:
        print(e)
        sys.exit(-1)


def save_result_to_file(image: Image, region: Region, image_file_name: str) -> None:
    # convert image to supported format to paint on it
    image_colored = image.convert_pixel_format(PixelFormat.RGB_8)

    # paint regions
    painter = Painter(image_colored)

    print("Painting the used image region in green.")
    painter.opacity = Opacity(25)
    painter.color = Color.create_from_rgb(0, 255, 0)
    image_region = image.region
    painter.draw(image_region)

    print("Painting threshold result in red.")
    painter.opacity = Opacity(100)
    painter.color = Color.create_from_rgb(255, 0, 0)
    painter.draw(region)

    # save image
    image_colored.save(image_file_name)
    print("Threshold image saved to", image_file_name)


if __name__ == "__main__":
    main()
