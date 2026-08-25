# Copyright(C) 2026, IDS Imaging Development Systems GmbH.
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
#

"""This script demonstrates how to use the device manager to open a camera in Python."""

import sys

from ids_peak_icv.datatypes.image import Image
from ids_peak import ids_peak
from ids_peak.buffer_guard import BufferGuard
from ids_peak.ids_peak import CommandNode, IntegerNode


def main() -> int:
    try:
        # Initialize libraries
        ids_peak.Library.Initialize()

        # Initialize DeviceManager and update device list
        device_manager = ids_peak.DeviceManager.Instance()
        device_manager.Update()

        # Find the first available camera with control access
        device_descriptor = device_manager.FirstAvailableDevice(
            ids_peak.DeviceAccessType_Control
        )

        if device_descriptor is None:
            raise Exception("Failed to find any openable camera!")

        # Open the device and get the nodemap of the remote device
        device = device_descriptor.OpenDevice(ids_peak.DeviceAccessType_Control)
        node_map_remote_device = device.RemoteDevice().NodeMaps()[0]

        # Open the data stream and prepare the buffers
        data_stream = device.DataStreams()[0].OpenDataStream()

        # Get the required payload size
        if data_stream.DefinesPayloadSize():
            payload_size = data_stream.PayloadSize()
        else:
            payload_size = node_map_remote_device["PayloadSize", IntegerNode].Value()

        buffer_count = data_stream.NumBuffersAnnouncedMinRequired()

        # Allocate buffers and queue them
        data_stream.AddAcquisitionBuffers(payload_size, buffer_count)

        # Lock transport layer parameters (TLParamsLocked = 1)
        node_map_remote_device["TLParamsLocked", IntegerNode].SetValue(1)

        # Start acquisition on both data stream and device
        data_stream.StartAcquisition()
        node_map_remote_device["AcquisitionStart", CommandNode].ExecuteAndWait()

        print("Acquisition started. Capturing 5 ICV images...")

        # Acquire 5 images and wrap them as ICV images
        for i in range(5):
            # Wait for a finished buffer (timeout: 5000 ms) and guard it
            with BufferGuard(data_stream.WaitForFinishedBuffer(5000)) as buffer:
                # Create an ICV image from the buffer's ImageView
                image = Image.create_from_image_view(
                    buffer.ToImageView()
                )

                # Process/Inspect the image
                pixel_data = image.to_numpy_array()

                print(
                    f"Image {i + 1} captured! "
                    f"Dimensions: {image.size}, "
                    f"PixelFormat: {image.pixel_format}, "
                    f"First pixel value: {pixel_data[0, 0]}"
                )

        # Stop acquisition
        node_map_remote_device["AcquisitionStop", CommandNode].ExecuteAndWait()
        data_stream.StopAcquisition(ids_peak.AcquisitionStopMode_Default)

        # Unlock transport layer parameters
        node_map_remote_device["TLParamsLocked", IntegerNode].SetValue(0)

        # Release acquisition buffers
        data_stream.FlushAndRevokeAllBuffers()

        print("Camera closed and resources released successfully.")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

    finally:
        # Close libraries
        ids_peak.Library.Close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
