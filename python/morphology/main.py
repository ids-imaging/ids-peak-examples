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


import sys

import numpy as np

from ids_peak_common import PixelFormat, Size, Rectangle
from ids_peak_icv import Image, Region, ICVException
from ids_peak_icv.painting import Painter


def main() -> None:
    try:
        region = Region.create_from_points(
            np.array([(2, 2),
                      (3, 2),
                      (4, 2),
                      (2, 3),
                      (3, 3),
                      (4, 3),
                      (2, 4),
                      (3, 4),
                      (4, 4),
                      (5, 4),
                      (3, 5)]))
        write_region_to_image_file(region, "region.png")

        structuring_element = Region.create_from_rectangle(
            Rectangle.create_from_coordinates_and_dimensions(-1, -1, 3, 3))

        # Apply Dilation
        region_dilated = region.dilation(structuring_element)
        write_region_to_image_file(region_dilated, "region_dilated.png")

        # Apply Erosion
        region_eroded = region.erosion(structuring_element)
        write_region_to_image_file(region_eroded, "region_eroded.png")


    except ICVException as e:
        print(e)
        sys.exit(e.status.value)
    except Exception as e:
        print(e)
        sys.exit(-1)


def create_checker_image(size: Size) -> Image:
    data = []
    for r in range(0, int(size.height)):
        for c in range(0, int(size.width)):
            val = 205
            if (r + c) % 2:
                val = 50
            data.append([[val, val, val]])
    array = np.array(data, dtype=PixelFormat.RGB_8.numpy_dtype)
    image = Image.create_from_np_array(PixelFormat.RGB_8, size, array)
    return image


def write_region_to_image_file(region: Region, file_name: str) -> None:
    image = create_checker_image(Size(8, 8))
    painter = Painter(image)
    painter.draw(region)
    image.save(file_name)


if __name__ == "__main__":
    main()
