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

import dataclasses
import re
from enum import IntEnum
from pathlib import Path
from typing import Sequence, cast
from abc import abstractmethod, ABC

import ids_peak
import numpy as np

from ids_peak_common import MetadataKey, PixelFormat, Channel, Interval
from ids_peak_icv import Image
from ids_peak_icv.experimental.hdr import HDR, ToneMapping

from camera import Camera, AcquisitionMode, UserSet


class HdrAcquisitionMode(IntEnum):
    """HDR acquisition modes."""

    AUTO = 0
    """
    Automatically selects the best available acquisition mode.
    """

    PROGRESSIVE = 1
    """
    In progressive mode the exposure value is changed programmatically before
    each image is captured.
    This mode works for every camera that changes exposure instantly.
    """

    SEQUENCER = 2
    """
    Sequencer mode uses the camera's sequencer feature which is preconfigured
    for the given exposure times.
    """

    QUAD_EXPOSURE = 3
    """
    Sensor feature for IMX900-based cameras that capture a single image
    using four distinct exposure times arranged in a 2×2 pixel pattern.
    """

    CLEAR_HDR = 4
    """
    Sensor feature for IMX675-based cameras that capture a single image
    using two gain factors in alternating lines starting with lower gain.
    """

    def __str__(self) -> str:
        return self.name


@dataclasses.dataclass
class HdrResult:
    """Result of an HDR capture operation."""
    image_sequence: Sequence[Image]
    hdr_image: Image
    ldr_image: Image


def create_exposure_sequence(exposure_range_s: Interval,
                             num_exposures: int) -> Sequence[float]:
    """Return a logarithmically spaced sequence of exposure times."""
    return [float(x) for x in
            np.logspace(np.log10(exposure_range_s.minimum),
                        np.log10(exposure_range_s.maximum), num_exposures)]


def compute_hdr(image_sequence: Sequence[Image]) -> HdrResult:
    """Compute HDR and LDR images from an input image sequence.

    The input images are combined into a single HDR image, which is then
    tone-mapped to produce a corresponding LDR image.

    Args:
        image_sequence: Sequence of images captured with different
            exposure settings.

    Returns:
        An `HdrCaptureResult` containing the original image sequence,
        the computed HDR image, and the tone-mapped LDR image.
    """

    hdr_processor = HDR()
    hdr_image = hdr_processor.process(np.array(image_sequence, dtype=object))

    tone_mapper = ToneMapping()
    ldr_image = tone_mapper.process(hdr_image)

    return HdrResult(image_sequence, hdr_image, ldr_image)


def calculate_hdr_image_from_directory(path: Path) -> HdrResult:
    """Read images from the given path and calculate the HDR image."""
    image_sequence: list[Image] = []

    pattern = re.compile(r"^seq\d+_\d+ms\d+\.png$")
    files = [f for f in path.iterdir() if
             f.is_file() and pattern.match(f.name)]

    def extract_ms(filename: str) -> float:
        exposures_pattern = re.compile(r"^seq\d+_(\d+)ms(\d+)\.png$")
        m = exposures_pattern.match(filename)
        if not m:
            raise RuntimeError(
                f"Failed to extract exposure time from file name {filename}")
        major_ms, minor_ms = m.groups()
        return float(f"{major_ms}.{minor_ms}")

    for file in files:
        image_exposure_ms = extract_ms(file.name)
        image = Image.create_from_file(str(file.absolute()))
        metadata = image.metadata
        metadata.set_value_by_key(
            MetadataKey.DEVICE_EXPOSURE_TIME, image_exposure_ms * 1000.0)
        image.metadata = metadata
        image_sequence.append(image)

    return compute_hdr(image_sequence)


def process_image(image: Image) -> Image:
    """Create an RGB_8 or MONO_8 ICV image from an image view,
    ensuring that the data is copied."""

    pixel_format = image.pixel_format
    if pixel_format in [PixelFormat.MONO_8, PixelFormat.RGB_8]:
        # return the image as copy of the original data
        return image.convert_pixel_format(pixel_format)

    if any(c in pixel_format.channels for c in
           [Channel.BAYER, Channel.RED, Channel.CHROMA_U]):
        return image.convert_pixel_format(PixelFormat.RGB_8)

    if pixel_format.has_intensity_channel:
        return image.convert_pixel_format(PixelFormat.MONO_8)

    raise RuntimeError("Unsupported pixel format!")


def process_interleaved_image(image: Image) -> list[Image]:
    image_sequence: list[Image] = image.deinterleave()

    return [process_image(image) for image in image_sequence]


class IHdrProvider(ABC):
    """Abstract interface for HDR provider."""

    @property
    @abstractmethod
    def mode(self) -> HdrAcquisitionMode:
        """HDR acquisition mode."""

    @abstractmethod
    def is_supported(self) -> bool:
        """Returns if the HDR provider is supported for the current camera."""

    @abstractmethod
    def configure(self, exposures_s: Sequence[float]) -> None:
        """Configures the HDR provider with the given exposure sequence."""

    @abstractmethod
    def acquire_hdr_image(self) -> HdrResult:
        """Acquires the image sequence and calculates the HDR result."""

    @abstractmethod
    def acquire_hdr_sequence(self) -> Sequence[Image]:
        """Acquires the HDR image sequence."""


class ProgressiveHdrProvider(IHdrProvider):
    """Implements progressive HDR by capturing a sequence of
    software-triggered images, adjusting the exposure time for each
    capture programmatically."""

    def __init__(self, camera: Camera) -> None:
        self._camera = camera
        self._device_exposure_sequence_s: Sequence[float] = []

    @property
    def mode(self) -> HdrAcquisitionMode:
        return HdrAcquisitionMode.PROGRESSIVE

    def is_supported(self) -> bool:
        return True

    def configure(self, exposure_sequence_s: Sequence[float]) -> None:
        if len(exposure_sequence_s) < 2:
            raise ValueError("A HDR image consists of at least 2 exposures.")

        self._device_exposure_sequence_s = exposure_sequence_s
        self._camera.set_acquisition_mode(AcquisitionMode.SOFTWARE_TRIGGER)

    def acquire_hdr_image(self) -> HdrResult:
        if not self.is_supported() or len(self._device_exposure_sequence_s) < 2:
            raise RuntimeError("HDR provider is not supported or configured!")

        self._camera.start_acquisition(len(self._device_exposure_sequence_s))
        image_sequence = self.acquire_hdr_sequence()
        self._camera.stop_acquisition()

        return compute_hdr(image_sequence)

    def acquire_hdr_sequence(self) -> Sequence[Image]:
        if not self.is_supported() or len(self._device_exposure_sequence_s) < 2:
            raise RuntimeError("HDR provider is not supported or configured!")

        image_sequence: list[Image] = []
        timeout: int = 5000

        for exposure_s in self._device_exposure_sequence_s:
            # camera needs exposure time in us
            exposure_us = exposure_s * 1_000_000
            self._camera.set_node_value("ExposureTime", exposure_us)

            buffer = self._camera.acquire_image_buffer(timeout)

            image = process_image(
                Image.create_from_image_view(buffer.ToImageView()))
            image_metadata = image.metadata
            image_metadata.set_value_by_key(
                MetadataKey.DEVICE_EXPOSURE_TIME,
                self._camera.get_node_value("ExposureTime"))
            image.metadata = image_metadata
            image_sequence.append(image)
            self._camera.queue_buffer(buffer)

        return image_sequence


class SequencerHdrProvider(IHdrProvider):
    """Implements HDR by capturing a predefined exposure sequence
    using the camera’s sequencer feature."""

    def __init__(self, camera: Camera) -> None:
        super().__init__()
        self._camera = camera
        self._device_exposure_sequence_s: list[float] = []
        self._is_supported = self._check_supported()

    @property
    def mode(self) -> HdrAcquisitionMode:
        return HdrAcquisitionMode.SEQUENCER

    def _check_supported(self) -> bool:
        sequencer_nodes = ["SequencerFeatureSelector",
                           "SequencerFeatureEnable",
                           "SequencerConfigurationMode",
                           "SequencerSetSelector",
                           "SequencerSetNext",
                           "SequencerPathSelector",
                           "SequencerTriggerSource",
                           "SequencerTriggerActivation",
                           "SequencerSetSave",
                           "SequencerMode"]
        if not self._camera.has_nodes(sequencer_nodes):
            return False

        try:
            self._camera.set_enum_node_entry("SequencerConfigurationMode",
                                             "On")

            self._camera.set_enum_node_entry("SequencerFeatureSelector",
                                             "ExposureTime")
            if self._camera.get_node_value("SequencerFeatureEnable") is False:
                self._camera.set_node_value("SequencerFeatureEnable", True)

            self._camera.set_enum_node_entry("SequencerConfigurationMode",
                                             "Off")
            return True
        except ids_peak.Exception:
            return False

    def is_supported(self) -> bool:
        return self._is_supported

    def configure(self, exposure_sequence_s: Sequence[float]) -> None:
        if len(exposure_sequence_s) < 2:
            raise ValueError("A HDR image consists of at least 2 exposures.")

        self._device_exposure_sequence_s.clear()

        try:
            # make sure that the sequencer mode is turned off for configuration
            self._camera.set_enum_node_entry("SequencerMode", "Off")
        except ids_peak.Exception:
            pass

        # turn on sequencer configuration mode
        self._camera.set_enum_node_entry("SequencerConfigurationMode", "On")

        for idx, exposure_s in enumerate(exposure_sequence_s):
            idx_next = (idx + 1) % len(exposure_sequence_s)

            # configure sequencer path
            self._camera.set_node_value("SequencerSetSelector", idx)
            self._camera.set_node_value("SequencerPathSelector", 0)
            self._camera.set_node_value("SequencerSetNext", idx_next)

            # configure sequencer trigger source
            self._camera.set_enum_node_entry("SequencerTriggerSource",
                                             "ExposureStart")
            self._camera.set_enum_node_entry("SequencerTriggerActivation",
                                             "RisingEdge")

            # configure sequence settings
            # self._camera needs exposure time in us
            exposure_time_us = exposure_s * 1_000_000
            self._camera.set_node_value("ExposureTime", exposure_time_us)

            device_exposure_s = cast(float, self._camera.get_node_value(
                "ExposureTime")) / 1_000_000
            self._device_exposure_sequence_s.append(device_exposure_s)

            # save sequence set configuration
            self._camera.exec_command_node_and_wait("SequencerSetSave")

        # turn off sequencer configuration mode
        self._camera.set_enum_node_entry("SequencerConfigurationMode", "Off")

        # enable software trigger
        self._camera.set_acquisition_mode(AcquisitionMode.SOFTWARE_TRIGGER)

        # turn on sequencer mode
        self._camera.set_enum_node_entry("SequencerMode", "On")

    def acquire_hdr_image(self) -> HdrResult:
        if not self.is_supported() or len(self._device_exposure_sequence_s) < 2:
            raise RuntimeError("HDR provider is not supported or configured!")

        self._camera.start_acquisition(len(self._device_exposure_sequence_s))
        image_sequence = self.acquire_hdr_sequence()
        self._camera.stop_acquisition()

        return compute_hdr(image_sequence)

    def acquire_hdr_sequence(self) -> Sequence[Image]:
        if not self.is_supported() or len(self._device_exposure_sequence_s) < 2:
            raise RuntimeError("HDR provider is not supported or configured!")

        image_sequence: list[Image] = []
        timeout: int = 5000

        for exposure_s in self._device_exposure_sequence_s:
            buffer = self._camera.acquire_image_buffer(timeout)

            image = process_image(
                Image.create_from_image_view(buffer.ToImageView()))
            image_metadata = image.metadata
            image_metadata.set_value_by_key(
                MetadataKey.DEVICE_EXPOSURE_TIME, exposure_s * 1_000_000)
            image.metadata = image_metadata
            image_sequence.append(image)
            self._camera.queue_buffer(buffer)

        return image_sequence


class QuadExposureHdrProvider(IHdrProvider):
    """HDR implementation for cameras with QuadHDR sensor support."""

    def __init__(self, camera: Camera) -> None:
        self._camera = camera
        self._device_exposure_sequence_s: list[float] = []
        self._is_supported = self._check_supported()

    @property
    def mode(self) -> HdrAcquisitionMode:
        return HdrAcquisitionMode.QUAD_EXPOSURE

    def _check_supported(self) -> bool:
        is_supported: bool = self._camera.has_enum_node_entry(
            "UserSetSelector", "QuadHDR")
        return is_supported

    def is_supported(self) -> bool:
        return self._is_supported

    def configure(self, exposure_sequence_s: Sequence[float]) -> None:
        if len(exposure_sequence_s) != 4:
            raise ValueError("Quad exposure needs exactly 4 exposures.")

        self._device_exposure_sequence_s.clear()

        self._camera.load_user_set(UserSet.QUAD_HDR)

        exposure_time_selector_entries = ["Pixel1", "Pixel2", "Pixel3",
                                          "Pixel4"]
        for index, exposure_s in enumerate(exposure_sequence_s):
            self._camera.set_enum_node_entry("ExposureTimeSelector",
                                             exposure_time_selector_entries[
                                                 index])
            exposure_us = exposure_s * 1_000_000
            self._camera.set_node_value("ExposureTime", exposure_us)

            device_exposure: float = cast(float, self._camera.get_node_value(
                "ExposureTime"))
            self._device_exposure_sequence_s.append(device_exposure / 1_000_000)

        self._camera.set_acquisition_mode(AcquisitionMode.FREERUN)
        self._camera.set_acquisition_frame_count(1)

    def acquire_hdr_image(self) -> HdrResult:
        if not self.is_supported() or len(
                self._device_exposure_sequence_s) != 4:
            raise RuntimeError("HDR provider is not supported or configured!")

        self._camera.start_acquisition(1)
        image_sequence = self.acquire_hdr_sequence()
        self._camera.stop_acquisition()

        return compute_hdr(image_sequence)

    def acquire_hdr_sequence(self) -> Sequence[Image]:
        if not self.is_supported() or len(
                self._device_exposure_sequence_s) != 4:
            raise RuntimeError("HDR provider is not supported or configured!")

        timeout: int = 5000

        buffer = self._camera.acquire_image_buffer(timeout)
        image = Image.create_from_image_view(buffer.ToImageView())

        metadata = image.metadata
        exposure_sequence_us = [e * 1_000_000 for e in
                                self._device_exposure_sequence_s]
        metadata.set_value_by_key(MetadataKey.DEVICE_EXPOSURE_TIME_SEQUENCE,
                                  exposure_sequence_us)
        image.metadata = metadata

        image_sequence = process_interleaved_image(image)

        self._camera.queue_buffer(buffer)

        return image_sequence


class ClearHdrProvider(IHdrProvider):
    """HDR implementation for cameras with ClearHDR sensor support."""

    def __init__(self, camera: Camera) -> None:
        self._camera = camera
        self._device_exposure_s: float = 0.0
        self._device_gains: list[float] = []
        self._is_supported = self._check_supported()

    @property
    def mode(self) -> HdrAcquisitionMode:
        return HdrAcquisitionMode.CLEAR_HDR

    def _check_supported(self) -> bool:
        is_supported: bool = self._camera.has_enum_node_entry(
            "UserSetSelector", "ClearHDR")
        return is_supported

    def is_supported(self) -> bool:
        return self._is_supported

    def configure(self, exposure_sequence_s: Sequence[float]) -> None:
        if len(exposure_sequence_s) != 2:
            raise ValueError("Clear hdr needs exactly 2 exposures.")

        self._device_gains.clear()

        self._camera.load_user_set(UserSet.CLEAR_HDR)

        it = iter(exposure_sequence_s)

        # set first as exposure
        exposure = next(it)
        self._camera.set_node_value("ExposureTime", exposure * 1_000_000)
        self._device_exposure_s = cast(float, self._camera.get_node_value(
            "ExposureTime")) / 1_000_000

        # set first gain value to 1
        self._camera.set_enum_node_entry("GainSelector", "AnalogLow")
        self._camera.set_node_value("Gain", 1.0)

        # calculate gain factor from second exposure
        gain = next(it) / exposure

        # set second gain value to calculated value
        self._camera.set_enum_node_entry("GainSelector", "AnalogHigh")
        self._camera.set_node_value("Gain", gain)

        device_gain: float = cast(float, self._camera.get_node_value("Gain"))
        self._device_gains.append(device_gain)
        # lower gain needs to be second in the list,
        # because the image sequence starts with the higher gain
        self._device_gains.append(1.0)

        self._camera.set_acquisition_mode(AcquisitionMode.FREERUN)
        self._camera.set_acquisition_frame_count(1)

    def acquire_hdr_image(self) -> HdrResult:
        if not self.is_supported() or len(self._device_gains) != 2:
            raise RuntimeError("HDR provider is not supported or configured!")

        self._camera.start_acquisition(1)
        image_sequence = self.acquire_hdr_sequence()
        self._camera.stop_acquisition()

        return compute_hdr(image_sequence)

    def acquire_hdr_sequence(self) -> Sequence[Image]:
        if not self.is_supported() or len(self._device_gains) != 2:
            raise RuntimeError("HDR provider is not supported or configured!")

        timeout: int = 5000

        buffer = self._camera.acquire_image_buffer(timeout)
        image = Image.create_from_image_view(buffer.ToImageView())

        metadata = image.metadata
        metadata.set_value_by_key(MetadataKey.DEVICE_EXPOSURE_TIME,
                                  self._device_exposure_s * 1_000_000)
        metadata.set_value_by_key(MetadataKey.DEVICE_GAIN_SEQUENCE,
                                  self._device_gains)

        image.metadata = metadata

        image_sequence = process_interleaved_image(image)

        self._camera.queue_buffer(buffer)

        return image_sequence


class HdrProviderRegistry:
    """Resolves and manages HDR providers for a given camera."""

    def __init__(self, camera: Camera) -> None:
        # Order for most efficient provider first
        preferred_providers = [ClearHdrProvider, QuadExposureHdrProvider,
                               SequencerHdrProvider,
                               ProgressiveHdrProvider]
        self._providers = [
            cls(camera)  # type: ignore[abstract]
            for cls in preferred_providers]

    @property
    def providers(self) -> Sequence[IHdrProvider]:
        """All registered HDR providers, ordered by preference."""
        return self._providers

    def get_provider(self,
                     hdr_acquisition_mode: HdrAcquisitionMode) -> IHdrProvider:
        """Return the supported HDR provider for the given acquisition mode.

        Raises:
            RuntimeError: If no supported provider exists for the given mode.
        """
        for provider in self._providers:
            if provider.is_supported() and (
                    hdr_acquisition_mode == HdrAcquisitionMode.AUTO or
                    provider.mode == hdr_acquisition_mode):
                return provider

        raise RuntimeError("No supported provider")

    @property
    def preferred_provider(self) -> IHdrProvider:
        """Return the most preferred supported HDR provider.

        Raises:
            RuntimeError: If no supported HDR provider is available.
        """
        return self.get_provider(HdrAcquisitionMode.AUTO)
