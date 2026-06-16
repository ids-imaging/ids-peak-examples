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
from typing import cast

import numpy as np
from ids_peak import ids_peak
from ids_peak.ids_peak import (
    Buffer,
    BufferPart,
    BufferPartType_Image2D,
    BufferPartType_Image3D,
    DataStream,
    DataStreamFlushMode_DiscardAll,
    Device,
    NodeMap,
    Timeout,
)
from ids_peak_common import Interval, Metadata, MetadataKey, PixelFormat, Rectangle
from ids_peak_icv import Image, PointCloud
from ids_peak_icv.calibration import CalibrationParameters
from ids_peak_icv.thresholds import Threshold
from ids_peak_icv.transformations import Undistortion

# --------------------------------------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------------------------------------

# Enable filtering of depth values based on the camera confidence image
FILTER_DEPTH_MAP_BY_CONFIDENCE_ENABLED: bool = True

# Pixels with confidence values below this threshold are marked as invalid. The Range is 0 to 4095.
CONFIDENCE_THRESHOLD: int = 100

# Camera exposure time in microseconds
EXPOSURE_TIME_US: float = 1000.0

# Enable filtering of depth values based on the Z distance
FILTER_DISTANCE_ENABLED: bool = True

# Valid Z distance interval in millimeters
FILTER_DISTANCE_INTERVAL_MM: Interval = Interval(100.0, 1000.0)

# Number of images acquired in this example
IMAGE_ACQUISITION_COUNT: int = 10

# --------------------------------------------------------------------------------------------------
# DEVICE UTILITIES
# --------------------------------------------------------------------------------------------------


# Open the first connected IDS Nion device
def open_first_connected_nion_device() -> tuple[Device, NodeMap]:
    instance = ids_peak.DeviceManager.Instance()
    instance.Update()

    devices = list(
        filter(
            lambda dev: dev.IsOpenable(ids_peak.DeviceAccessType_Control)
            and dev.ModelName().find("NION") != -1,
            instance.Devices(),
        )
    )

    if len(devices) == 0:
        print("No IDS Nion device found.")
        raise SystemExit("Failed to open camera")

    device = devices[0].OpenDevice(ids_peak.DeviceAccessType_Control)
    node_map: NodeMap = device.RemoteDevice().NodeMaps()[0]

    return device, node_map


def device_reset_to_default(node_map: NodeMap) -> None:
    cast(
        ids_peak.EnumerationNode,
        node_map.FindNode("UserSetSelector"),
    ).SetCurrentEntry("Default")
    cast(
        ids_peak.CommandNode,
        node_map.FindNode("UserSetLoad"),
    ).Execute()


def device_set_confidence_threshold(node_map: NodeMap, confidence_threshold: int) -> None:
    cast(
        ids_peak.IntegerNode,
        node_map.FindNode("Scan3dRangeConfidenceThreshold"),
    ).SetValue(confidence_threshold)


def device_set_exposure_time(node_map: NodeMap, exposure_time_us: float) -> None:
    cast(
        ids_peak.FloatNode,
        node_map.FindNode("ExposureTime"),
    ).SetValue(float(exposure_time_us))


def device_read_calibration_parameters(node_map: NodeMap) -> CalibrationParameters:
    adapter = ids_peak.FileAdapter(node_map, "LensCalibrationData")

    if adapter is None:
        raise SystemExit("No factory calibration data available.")

    return CalibrationParameters.create_from_binary(
        np.frombuffer(adapter.Read(adapter.Size()), np.uint8)
    )


def device_get_depth_minimum_valid_value(node_map: NodeMap) -> float:
    value = cast(
        ids_peak.FloatNode,
        node_map.FindNode("Scan3dAxisMin"),
    ).Value()

    return cast(float, value)


def device_get_depth_maximum_valid_value(node_map: NodeMap) -> float:
    value = cast(
        ids_peak.FloatNode,
        node_map.FindNode("Scan3dAxisMax"),
    ).Value()

    return cast(float, value)


# Get the scale factor for converting depth values into metric units
def device_get_depth_scale_factor(node_map: NodeMap) -> float:
    value = cast(
        ids_peak.FloatNode,
        node_map.FindNode("Scan3dCoordinateScale"),
    ).Value()

    return cast(float, value)


# Create a metadata object containing binning and ROI information
# The metadata is required for correct undistortion of images.
# Note: This example assumes that the camera settings for binning
# and ROI remain unchanged for each image.
# However, if these conditions change, it is advisable to refer to the chunk data.
def device_get_image_metadata(node_map: NodeMap) -> Metadata:
    metadata = Metadata()

    metadata.set_value_by_key(
        MetadataKey.BINNING_HORIZONTAL,
        cast(
            ids_peak.IntegerNode,
            node_map.FindNode("BinningHorizontal"),
        ).Value(),
    )
    metadata.set_value_by_key(
        MetadataKey.BINNING_VERTICAL,
        cast(
            ids_peak.IntegerNode,
            node_map.FindNode("BinningVertical"),
        ).Value(),
    )

    offset_x = cast(
        ids_peak.IntegerNode,
        node_map.FindNode("OffsetX"),
    ).Value()
    offset_y = cast(
        ids_peak.IntegerNode,
        node_map.FindNode("OffsetY"),
    ).Value()
    width = cast(
        ids_peak.IntegerNode,
        node_map.FindNode("Width"),
    ).Value()
    height = cast(
        ids_peak.IntegerNode,
        node_map.FindNode("Height"),
    ).Value()

    metadata.set_value_by_key(
        MetadataKey.ROI,
        Rectangle.create_from_coordinates_and_dimensions(offset_x, offset_y, width, height),
    )

    return metadata


# --------------------------------------------------------------------------------------------------
# ACQUISITION
# --------------------------------------------------------------------------------------------------


# Start image acquisition and prepare the data stream
def device_start_acquisition(device: Device, node_map: NodeMap) -> DataStream:
    data_stream = device.DataStreams()[0].OpenDataStream()

    cast(
        ids_peak.EnumerationNode,
        node_map.FindNode("AcquisitionMode"),
    ).SetCurrentEntry("Continuous")

    payload_size = cast(
        ids_peak.IntegerNode,
        node_map.FindNode("PayloadSize"),
    ).Value()

    for _ in range(data_stream.NumBuffersAnnouncedMinRequired()):
        # Let the transport layer allocate the buffers for easier memory management.
        buffer = data_stream.AllocAndAnnounceBuffer(payload_size)
        # Queue the buffer so that the datastream is allowed to fill it with image data.
        data_stream.QueueBuffer(buffer)

    cast(
        ids_peak.IntegerNode,
        node_map.FindNode("TLParamsLocked"),
    ).SetValue(1)

    data_stream.StartAcquisition()
    cast(
        ids_peak.CommandNode,
        node_map.FindNode("AcquisitionStart"),
    ).Execute()
    cast(
        ids_peak.CommandNode,
        node_map.FindNode("AcquisitionStart"),
    ).WaitUntilDone()

    return data_stream


# Extract depth and intensity images from a multipart buffer
def extract_buffer_parts(buffer: Buffer) -> tuple[BufferPart, BufferPart]:
    parts = buffer.Parts()

    def get_part(buffer_type: int) -> BufferPart:
        try:
            return next(p for p in parts if p.Type() == buffer_type)
        except StopIteration as exception:
            raise SystemExit(f"Missing buffer part: {buffer_type}") from exception

    return get_part(BufferPartType_Image3D), get_part(BufferPartType_Image2D)


# Stop acquisition and release buffers
def device_stop_acquisition(node_map: NodeMap, data_stream: DataStream) -> None:
    cast(
        ids_peak.CommandNode,
        node_map.FindNode("AcquisitionStop"),
    ).Execute()
    cast(
        ids_peak.CommandNode,
        node_map.FindNode("AcquisitionStop"),
    ).WaitUntilDone()

    data_stream.StopAcquisition()
    cast(
        ids_peak.IntegerNode,
        node_map.FindNode("TLParamsLocked"),
    ).SetValue(0)

    data_stream.Flush(DataStreamFlushMode_DiscardAll)

    for buffer in data_stream.AnnouncedBuffers():
        data_stream.RevokeBuffer(buffer)


# --------------------------------------------------------------------------------------------------
# FILE OUTPUT
# --------------------------------------------------------------------------------------------------


def get_output_file_path(file_name: str) -> str:
    if os.name == "posix":
        return os.path.join("/tmp", file_name)
    else:
        return os.path.join("C:/Users/Public/Pictures", file_name)


def write_depth_map_to_file(depth_map: Image, i: int) -> None:
    # When written to file the set region is ignored and
    # all pixels are displayed if you want to change this
    # you have to paint the unused pixels with the Painter class
    undistorted_depth_map_file_path = get_output_file_path(f"undistorted_depth_map_{i}.tiff")
    depth_map.save(undistorted_depth_map_file_path)
    print(f"Undistorted depth map written to: {undistorted_depth_map_file_path}")


def write_intensity_to_file(intensity: Image, i: int) -> None:
    undistorted_intensity_image_file_path = get_output_file_path(
        f"undistorted_intensity_image_{i}.png"
    )
    intensity.save(undistorted_intensity_image_file_path)
    print(f"Undistorted intensity image written to: {undistorted_intensity_image_file_path}")


def write_point_cloud_to_file(point_cloud: PointCloud, i: int) -> None:
    point_cloud_file_path = get_output_file_path(f"point_cloud_xyzi_{i}.ply")
    point_cloud.save(point_cloud_file_path)
    print(f"Point cloud written to: {point_cloud_file_path}")


# --------------------------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------------------------


def main() -> None:
    try:
        ids_peak.Library.Initialize()

        device, node_map = open_first_connected_nion_device()

        device_reset_to_default(node_map)

        if FILTER_DEPTH_MAP_BY_CONFIDENCE_ENABLED:
            device_set_confidence_threshold(node_map, CONFIDENCE_THRESHOLD)

        device_set_exposure_time(node_map, EXPOSURE_TIME_US)

        calibration = device_read_calibration_parameters(node_map)
        minimum_valid_value = device_get_depth_minimum_valid_value(node_map)
        maximum_valid_value = device_get_depth_maximum_valid_value(node_map)
        scale_factor = device_get_depth_scale_factor(node_map)
        metadata = device_get_image_metadata(node_map)

        # Undistortion object initialized with factory calibration data
        undistortion = Undistortion.create_from_intrinsics(calibration.intrinsic_parameters)

        stream = device_start_acquisition(device, node_map)

        for i in range(IMAGE_ACQUISITION_COUNT):
            buffer = stream.WaitForFinishedBuffer(Timeout(5000))

            if buffer.IsIncomplete():
                print(f"Incomplete buffer {i}. Skipping.")
                stream.QueueBuffer(buffer)
                continue

            if not buffer.HasNewData():
                print(f"Buffer {i} has no new data. Skipping.")
                stream.QueueBuffer(buffer)
                continue

            if not buffer.HasParts():
                raise SystemExit("Buffer has no parts. Aborting.")

            depth_map_part, intensity_part = extract_buffer_parts(buffer)

            # --------------------------------------------------------------------------------------
            # Depth map processing
            # --------------------------------------------------------------------------------------

            # Create image from raw depth buffer and attach metadata
            raw_depth = Image.create_from_image_view(depth_map_part.ToImageView())
            raw_depth.metadata = metadata

            # Convert depth values to floating-point metric coordinates
            depth = raw_depth.convert_pixel_format_with_factor(
                PixelFormat.COORD3D_C32F, scale_factor
            )

            # Remove invalid depth pixels and get region of only valid pixels
            valid_pixel_threshold = Threshold(Interval(minimum_valid_value, maximum_valid_value))
            depth.region = valid_pixel_threshold.process(depth)

            # Undistort the depth map
            undistorted_depth = undistortion.process(depth)

            # Optional distance-based filtering
            if FILTER_DISTANCE_ENABLED:
                distance_filter = Threshold(FILTER_DISTANCE_INTERVAL_MM)
                undistorted_depth.region = distance_filter.process(undistorted_depth)

            write_depth_map_to_file(undistorted_depth, i)

            # --------------------------------------------------------------------------------------
            # Intensity image processing
            # --------------------------------------------------------------------------------------

            intensity = Image.create_from_image_view(intensity_part.ToImageView())
            intensity.metadata = metadata

            undistorted_intensity = undistortion.process(intensity)
            write_intensity_to_file(undistorted_intensity, i)

            # Queue buffer that it can be reused. This can be done after the buffer data is no
            # longer used.
            stream.QueueBuffer(buffer)

            # --------------------------------------------------------------------------------------
            # Point cloud generation
            # --------------------------------------------------------------------------------------

            point_cloud = PointCloud.create_from_undistorted_depth_map(
                undistorted_depth, undistorted_intensity
            )

            # Applies the extrinsic calibration parameters from the factory calibration
            # to shift the coordinate system's origin
            # from the optical center directly to the front housing of the Nion camera.
            # Alternatively, a workspace calibration can be performed
            # to define the origin at any desired location within the scene.
            transformed_point_cloud = point_cloud.transform_to_workspace(
                calibration.extrinsic_parameters
            )

            write_point_cloud_to_file(transformed_point_cloud, i)

        device_stop_acquisition(node_map, stream)

    except Exception as e:
        print(e)

    ids_peak.Library.Close()


if __name__ == "__main__":
    main()
