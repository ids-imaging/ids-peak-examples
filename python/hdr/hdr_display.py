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

from typing import Sequence

import numpy as np
from matplotlib import pyplot as plt

from ids_peak_common import PixelFormat, Channel, MetadataKey
from ids_peak_icv import Image

import hdr


def display_hdr_result(hdr_capture: hdr.HdrResult) -> None:
    """Display the captured image sequence and the calculated HDR image."""
    plt.ion()  # enable interactive mode for non-blocking display

    _display_image_sequence(hdr_capture.image_sequence)

    _display_hdr_image_preview(hdr_capture.ldr_image,
                               hdr_capture.hdr_image)

    plt.ioff()  # turn off interactive mode
    plt.show()  # blocks until all figure windows are closed


def _is_bgr(image: Image) -> bool:
    return (image.pixel_format.has_channel(Channel.BLUE)
            and image.pixel_format.number_of_channels in [3, 4]
            and image.pixel_format.get_channel_index(Channel.BLUE) == 0)


def _is_mono(image: Image) -> bool:
    return (image.pixel_format.has_channel(Channel.INTENSITY)
            and image.pixel_format.is_single_channel)


def _display_image_sequence(image_sequence: Sequence[Image]) -> None:
    fig, axes = plt.subplots(1, len(image_sequence), figsize=(14, 4),
                             constrained_layout=True)
    fig.suptitle("Captured Image Sequence", fontsize=16)

    for idx, image in enumerate(image_sequence):
        metadata = image.metadata
        exposure_ms = metadata.get_value_by_key(
            MetadataKey.DEVICE_EXPOSURE_TIME) / 1000
        if metadata.has_entry_by_key(MetadataKey.DEVICE_GAIN):
            exposure_ms = exposure_ms * metadata.get_value_by_key(
                MetadataKey.DEVICE_GAIN)

        ax = axes[idx]
        ax.set_title(f"Exposure: {exposure_ms:.3f} ms")
        ax.axis("off")

        if _is_bgr(image):
            img = image.convert_pixel_format(
                PixelFormat.RGB_8).to_numpy_array()
        else:
            img = image.to_numpy_array()

        if _is_mono(image):
            ax.imshow(img.astype("uint8"), cmap="gray", vmin=0, vmax=255)
        else:
            ax.imshow(img.astype("uint8"))

    plt.pause(0.01)


def _display_hdr_image_preview(ldr_image: Image,
                               hdr_image: Image) -> None:
    # Create figure with two rows: image on top, histogram below
    fig, axes = plt.subplots(2, 1, height_ratios=[7, 2])
    fig.suptitle("HDR image", fontsize=16)

    # --- Image display ---
    ax_img = axes[0]
    ax_img.axis("off")
    color_map = "gray" if _is_mono(ldr_image) else None
    ax_img.imshow(ldr_image.to_numpy_array(), cmap=color_map, vmin=0.0,
                  vmax=255.0)

    # --- Histogram display (EV domain) ---
    ax_hist = axes[1]
    ax_hist.set_title("Histogram (in EV)")
    ax_hist.set_xlabel("Exposure Value (EV)")
    ax_hist.yaxis.set_visible(False)

    # Convert to EV (relative to normalized white = EV 0)
    flat_img = hdr_image.to_numpy_array().ravel()
    img_filtered = flat_img[(flat_img != 0.0) & np.isfinite(flat_img)]
    img_ev = np.log2(img_filtered)
    ax_hist.hist(img_ev, bins=256, histtype="stepfilled")

    fig.subplots_adjust(hspace=0.3)
    fig.tight_layout()
    plt.pause(0.01)
