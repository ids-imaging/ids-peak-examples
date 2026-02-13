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
import time
import argparse
import dataclasses
from pathlib import Path

import cv2

import ids_peak_common
from ids_peak_common import MetadataKey
from ids_peak import ids_peak

from camera import Camera
import hdr
from hdr_display import display_hdr_result


@dataclasses.dataclass
class _AppArgs:
    exposure_range_s: ids_peak_common.Interval
    serial_number: str | None
    no_gui: bool
    output_directory: Path | None
    input_directory: Path | None
    num_exposures: int
    hdr_acquisition_mode: hdr.HdrAcquisitionMode


def _save_hdr_result(path: Path,
                     hdr_result: hdr.HdrResult) -> None:
    if not os.path.exists(path):
        os.makedirs(path)

    for idx, seq_image in enumerate(
            hdr_result.image_sequence):
        metadata = seq_image.metadata
        exposure_ms = metadata.get_value_by_key(
            MetadataKey.DEVICE_EXPOSURE_TIME) / 1000
        if metadata.has_entry_by_key(MetadataKey.DEVICE_GAIN):
            exposure_ms = exposure_ms * metadata.get_value_by_key(
                MetadataKey.DEVICE_GAIN)

        exposure_ms_str = f"{exposure_ms:.3f}".replace(".", "ms")
        file_name = path / f"seq{idx}_{exposure_ms_str}.png"
        seq_image.save(str(file_name.absolute()))
        print(f"Saving sequence image to {file_name}")

    hdr_preview_image_path = path / "hdr_preview_8bit.png"
    hdr_result.ldr_image.save(str(hdr_preview_image_path.absolute()))
    print(f"Saving hdr preview image to {hdr_preview_image_path}")

    hdr_image_path_tiff = path / "hdr_image.tiff"
    hdr_result.hdr_image.save(str(hdr_image_path_tiff.absolute()))
    print(f"Saving hdr image to {hdr_image_path_tiff}")

    hdr_image_path_hdr = path / "hdr_image.hdr"
    try:
        # cv expects images in bgr format
        img = hdr_result.hdr_image
        hdr_bgr = cv2.cvtColor(img.to_numpy_array(False), cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(hdr_image_path_hdr.absolute()), hdr_bgr)
        print(f"Saving hdr image to {hdr_image_path_hdr}")
    except Exception as e:
        print(f"Unable to save hdr image to {hdr_image_path_hdr}: {e}")


def _handle_exception(e: Exception, no_gui: bool) -> None:
    if no_gui:
        print("Error!", e)
    else:
        from tkinter import messagebox
        messagebox.showerror("Error", str(e))


def _process_saved_images(app_config: _AppArgs) -> None:
    assert app_config.input_directory is not None
    try:
        # (1.) Load images from disk and create HDR image
        hdr_result = hdr.calculate_hdr_image_from_directory(
            app_config.input_directory)

        # (2.) Save images to disk
        if app_config.output_directory is not None:
            _save_hdr_result(app_config.output_directory, hdr_result)

        # (3.) Display HDR image
        if not app_config.no_gui:
            display_hdr_result(hdr_result)

    except Exception as e:
        _handle_exception(e, app_config.no_gui)


def main(app_config: _AppArgs) -> None:
    """Main function."""
    if app_config.input_directory is not None:
        _process_saved_images(app_config)
        return

    ids_peak.Library.Initialize()

    try:
        # 1. Open device and reset to default
        if app_config.serial_number is None:
            camera = Camera.open_first_available()
        else:
            camera = Camera.open_by_serial_number(app_config.serial_number)

        camera.reset_to_default()

        # 2. Find which HDR option is available
        hdr_provider_registry = hdr.HdrProviderRegistry(camera)
        providers = hdr_provider_registry.providers
        print(
            f"Available HDR image acquisition modes: "
            f"{', '.join(str(x.mode) for x in providers if x.is_supported())}")

        # 3. Configure HDR option
        if app_config.hdr_acquisition_mode is hdr.HdrAcquisitionMode.AUTO:
            provider = hdr_provider_registry.preferred_provider
        else:
            provider = hdr_provider_registry.get_provider(
                app_config.hdr_acquisition_mode)
            if not provider.is_supported():
                raise RuntimeError(
                    f"Acquisition mode {app_config.hdr_acquisition_mode} "
                    f"is not supported by this device.")
        print(f"Using mode {provider.mode} for HDR image acquisition.")

        exposure_sequence_s = hdr.create_exposure_sequence(
            app_config.exposure_range_s, app_config.num_exposures)
        provider.configure(exposure_sequence_s)

        # 4. Capture image sequence
        exposure_sequence_str = ", ".join(
            [f"{float(x) * 1000.0:.3f}ms" for x in exposure_sequence_s])
        print(f"Capturing {len(exposure_sequence_s)} images")
        print(f"  - Exposures: {exposure_sequence_str}")
        start = time.time()
        hdr_result = provider.acquire_hdr_image()
        print(f"Capture took {int((time.time() - start) * 1000)} ms")

        # (5.) Save images to disk
        if app_config.output_directory is not None:
            _save_hdr_result(app_config.output_directory, hdr_result)

        # (6.) Display HDR image
        if not app_config.no_gui:
            display_hdr_result(hdr_result)

        camera.reset_to_default()

    except Exception as e:
        _handle_exception(e, app_config.no_gui)

    finally:
        ids_peak.Library.Close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Capture a series of images to calculate an HDR image.")
    parser.add_argument("--min", type=float,
                        help="Minimum exposure value in milliseconds "
                             "(must be given together with --max)")
    parser.add_argument("--max", type=float,
                        help="Maximum exposure value in milliseconds "
                             "(must be given together with --min)")
    parser.add_argument("-n", "--num-exposures", type=int, default=4,
                        help="Number of exposures to capture for HDR, "
                             "spaced logarithmically across the specified "
                             "exposure range.")
    parser.add_argument("-s", "--serial", type=str,
                        help="Serial number of the camera to open.")
    parser.add_argument("--no-gui", action="store_true",
                        help="Do not show GUI elements, only console outputs.")
    parser.add_argument("-o", "--out-dir", type=Path,
                        help="Directory to save sequence images and "
                             "generated LDR/HDR results.")
    parser.add_argument("-i", "--in-dir", type=Path,
                        help="Use images from directory instead to capture "
                             "camera images.")
    parser.add_argument("-a", "--acquisition-mode",
                        type=lambda s: hdr.HdrAcquisitionMode[s.upper()],
                        choices=list(hdr.HdrAcquisitionMode),
                        default=hdr.HdrAcquisitionMode.AUTO,
                        help="Mode used to capture the image sequence.")

    args = parser.parse_args()

    # Both-or-none check
    if (args.min is None) != (args.max is None):
        parser.error("You must provide both --min and --max, or neither.")

    # Set defaults if none are provided
    if args.min is None and args.max is None:
        exposure_range_s = ids_peak_common.Interval(0.0005, 0.05)
    else:
        exposure_range_s = ids_peak_common.Interval(args.min / 1_000.0,
                                                    args.max / 1_000.0)

    main(_AppArgs(exposure_range_s=exposure_range_s,
                  serial_number=args.serial,
                  no_gui=args.no_gui,
                  output_directory=args.out_dir,
                  input_directory=args.in_dir,
                  num_exposures=args.num_exposures,
                  hdr_acquisition_mode=args.acquisition_mode))
