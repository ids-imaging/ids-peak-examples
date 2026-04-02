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

from ids_peak_common import Interval, PixelFormat
from ids_peak_icv import Image, ICVException
from ids_peak_icv.selectors import RegionSelector
from ids_peak_icv.thresholds import Threshold
from ids_peak_icv.painting import Painter, ColorPaletteConstant


def main() -> None:
    try:
        # Load image
        script_path = os.path.dirname(os.path.realpath(__file__))
        image = Image.create_from_file(
            os.path.join(script_path, "../../data/threshold_from_file/beads.png"))

        # Apply a threshold in the range 25 to 255
        threshold = Threshold(Interval(25, 255))
        region = threshold.process(image)

        # split connected regions
        connected_regions = region.connected_components

        # select regions
        selector = RegionSelector(connected_regions)
        selection_dark_stones = selector.select_by_area(Interval(150, 300))

        # convert image to supported format to paint on it
        image_colored = image.convert_pixel_format(PixelFormat.RGB_8)

        # paint regions
        painter = Painter(image_colored)
        painter.color = ColorPaletteConstant.COLORED_6
        for region in selection_dark_stones.regions:
            painter.draw(region)

        # console output
        print("Number of found regions: {number}".format(number=len(selection_dark_stones.regions)))

        output_image_path = "image_thresholded.png"

        # save image
        image_colored.save(output_image_path)
        print("Threshold image saved to", output_image_path)
    except ICVException as e:
        print(e)
        sys.exit(e.status.value)
    except Exception as e:
        print(e)
        sys.exit(-1)


if __name__ == "__main__":
    main()
