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

import math
import sys
from dataclasses import dataclass
from typing import cast

import numpy as np
from ids_peak import ids_peak
from ids_peak.buffer_guard import BufferGuard
from ids_peak.ids_peak import (
    BooleanNode,
    CommandNode,
    DataStream,
    Device,
    EnumerationNode,
    FloatNode,
    IntegerNode,
    NodeMap,
    Timeout,
)
from ids_peak_common import PixelFormat
from ids_peak_icv import Image

# --------------------------------------------------------------------------------------------------
# CONFIGURATION
# --------------------------------------------------------------------------------------------------

STARTING_POINT_MM: float = 450.0
IMAGE_ACQUISITION_COUNT: int = 1


def open_first_connected_nion_device() -> tuple[Device, NodeMap]:
    device_manager = ids_peak.DeviceManager.Instance()
    device_manager.Update()

    devices = [
        device
        for device in device_manager.Devices()
        if device.IsOpenable(ids_peak.DeviceAccessType_Control)
        and "nion" in device.ModelName().lower()
    ]

    if not devices:
        raise RuntimeError("No IDS Nion device found.")

    device = devices[0].OpenDevice(ids_peak.DeviceAccessType_Control)
    node_map = device.RemoteDevice().NodeMaps()[0]
    return device, node_map


def device_reset_to_default(node_map: NodeMap) -> None:
    cast(
        EnumerationNode,
        node_map.FindNode("UserSetSelector"),
    ).SetCurrentEntry("Default")
    cast(
        CommandNode,
        node_map.FindNode("UserSetLoad"),
    ).ExecuteAndWait()


def device_start_acquisition(device: Device, node_map: NodeMap) -> DataStream:
    cast(
        EnumerationNode,
        node_map.FindNode("ComponentSelector"),
    ).SetCurrentEntry("Intensity")
    cast(
        BooleanNode,
        node_map.FindNode("ComponentEnable"),
    ).SetValue(False)

    cast(
        EnumerationNode,
        node_map.FindNode("ComponentSelector"),
    ).SetCurrentEntry("Confidence")
    cast(
        BooleanNode,
        node_map.FindNode("ComponentEnable"),
    ).SetValue(False)

    data_stream = device.DataStreams()[0].OpenDataStream()
    cast(
        EnumerationNode,
        node_map.FindNode("AcquisitionMode"),
    ).SetCurrentEntry("Continuous")

    payload_size = cast(
        IntegerNode,
        node_map.FindNode("PayloadSize"),
    ).Value()
    data_stream.AddAcquisitionBuffers(
        payload_size,
        data_stream.NumBuffersAnnouncedMinRequired(),
    )

    cast(
        IntegerNode,
        node_map.FindNode("TLParamsLocked"),
    ).SetValue(1)

    data_stream.StartAcquisition()
    cast(
        CommandNode,
        node_map.FindNode("AcquisitionStart"),
    ).ExecuteAndWait()

    return data_stream


def device_stop_acquisition(node_map: NodeMap, data_stream: DataStream) -> None:
    cast(
        CommandNode,
        node_map.FindNode("AcquisitionStop"),
    ).ExecuteAndWait()
    data_stream.StopAcquisition()

    cast(
        IntegerNode,
        node_map.FindNode("TLParamsLocked"),
    ).SetValue(0)
    data_stream.FlushAndRevokeAllBuffers()


@dataclass
class UnambiguousRangeData:
    starting_point_dn: int
    scan3d_axis_max: int
    scale_factor: float
    coordinate_offset: float
    invalid_data_value_dn: int


def main() -> int:
    try:
        ids_peak.Library.Initialize()

        device, node_map = open_first_connected_nion_device()
        device_reset_to_default(node_map)

        # note: Scan3dCoordinateScale changes when unambiguous range is changed.
        scale_factor = cast(
            FloatNode,
            node_map.FindNode("Scan3dCoordinateScale"),
        ).Value()
        coordinate_offset = cast(
            FloatNode,
            node_map.FindNode("Scan3dCoordinateOffset"),
        ).Value()
        # note: Scan3dAxisMax does not change when unambiguous range is changed.
        # The IDS Nion camera will always return values in the range [0, Scan3dAxisMax]
        # for the depth map, regardless
        # of the unambiguous range setting.
        scan3d_axis_max = int(
            cast(
                FloatNode,
                node_map.FindNode("Scan3dAxisMax"),
            ).Value()
        )
        invalid_data_value_dn = int(
            cast(
                FloatNode,
                node_map.FindNode("Scan3dInvalidDataValue"),
            ).Value()
        )

        # Use Scan3dCoordinateScale to convert the unambiguous range
        # from millimeters to DN (digital number) values
        # and the other way around.
        starting_point_dn = math.floor(STARTING_POINT_MM / scale_factor + 0.5)

        data_stream = device_start_acquisition(device, node_map)

        unambiguous_range_data = UnambiguousRangeData(
            starting_point_dn=starting_point_dn,
            scan3d_axis_max=scan3d_axis_max,
            scale_factor=scale_factor,
            coordinate_offset=coordinate_offset,
            invalid_data_value_dn=invalid_data_value_dn,
        )

        def create_unambiguous_depth_map(
            raw_depth: Image,
            unambiguous_range_data: UnambiguousRangeData,
        ) -> Image:
            raw_values = raw_depth.to_numpy_array()
            invalid_pixels = raw_values == unambiguous_range_data.invalid_data_value_dn

            range_maximum_dn = (
                unambiguous_range_data.starting_point_dn + unambiguous_range_data.scan3d_axis_max
            )
            range_span_dn = range_maximum_dn - unambiguous_range_data.starting_point_dn + 1
            remainder_of_ambiguous_range = range_span_dn - unambiguous_range_data.starting_point_dn
            values_dn = raw_values.astype(np.int64)
            shifted_values_dn = (
                np.remainder(values_dn + remainder_of_ambiguous_range, range_span_dn)
                + unambiguous_range_data.starting_point_dn
            )

            depth_values = shifted_values_dn.astype(np.float32) * np.float32(
                unambiguous_range_data.scale_factor
            ) + np.float32(unambiguous_range_data.coordinate_offset)
            depth_values[invalid_pixels] = np.float32(unambiguous_range_data.invalid_data_value_dn)

            return Image.create_from_np_array(
                PixelFormat.COORD3D_C32F,
                raw_depth.size,
                depth_values,
            )

        for i in range(IMAGE_ACQUISITION_COUNT):
            with BufferGuard(data_stream.WaitForFinishedBuffer(Timeout(5000))) as buffer:
                if buffer.IsIncomplete():
                    print(f"Incomplete buffer {i}. Skipping.")
                    continue
                if not buffer.HasNewData():
                    print(f"Buffer {i} has no new data. Skipping.")
                    continue

                raw_depth = Image.create_from_image_view(buffer.ToImageView())
                depth_map = create_unambiguous_depth_map(
                    raw_depth,
                    unambiguous_range_data,
                )

                data_stream.QueueBuffer(buffer)

                output_path = f"depth_map_{i}.tiff"
                depth_map.save(output_path)
                print(f"Depth map written to: {output_path}")

    except Exception as exception:
        print(f"Error: {exception}", file=sys.stderr)
        return 1
    finally:
        ids_peak.Library.Close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
