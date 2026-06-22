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

from typing import cast

from ids_peak import ids_peak
from ids_peak_icv import Image


def main() -> None:
    # The library must be initialized before use.
    # Each `Initialize` call must be matched with a corresponding call
    # to `Close`.
    ids_peak.Library.Initialize()

    # Create a device manager object
    device_manager = ids_peak.DeviceManager.Instance()

    try:
        # Update the device manager.
        # When `Update` is called, it searches for all producer libraries
        # contained in the directories found in the official GenICam GenTL
        # environment variable GENICAM_GENTL{32/64}_PATH. It then opens all
        # found ProducerLibraries, their Systems, their Interfaces, and lists
        # all available DeviceDescriptors.
        device_manager.Update()

        # Create a list with all openable devices.
        devices = list(
            filter(
                lambda dev: dev.IsOpenable(ids_peak.DeviceAccessType_Control),
                device_manager.Devices(),
            )
        )

        # Exit program if no device was found.
        if len(devices) == 0:
            print("No openable device found. Exiting Program.")
            return

        # Open the first openable device with control access.
        # The access types correspond to the GenTL `DEVICE_ACCESS_FLAGS`.
        device = device_manager.Devices()[0].OpenDevice(
            ids_peak.DeviceAccessType_Control
        )

        # Retrieve the remote device's primary node map, which in GenICam represents
        # a hierarchical set of device parameters (features) such as exposure, gain,
        # and firmware info. The remote nodemap provides access to controls implemented
        # on the device itself, primarily following the GenICam Standard Feature
        # Naming Convention (SFNC), while also supporting custom nodes to
        # accommodate device-specific features.
        nodemap_remote_device = device.RemoteDevice().NodeMaps()[0]

        data_stream = device.DataStreams()[0].OpenDataStream()

        payload_size = cast(ids_peak.IntegerNode,
                            nodemap_remote_device.FindNode("PayloadSize")).Value()

        # Minimum number of required buffers
        buffer_count_max = data_stream.NumBuffersAnnouncedMinRequired()

        # Allocate buffers and add them to the pool
        for _ in range(buffer_count_max):
            # Let the TL allocate the buffers
            buffer = data_stream.AllocAndAnnounceBuffer(payload_size)
            # Put the buffer in the pool
            data_stream.QueueBuffer(buffer)

        # Lock writable nodes, which could influence the payload size or
        # similar information during acquisition.
        cast(ids_peak.IntegerNode, nodemap_remote_device.FindNode("TLParamsLocked")).SetValue(1)

        print("Starting acquisition...")
        data_stream.StartAcquisition()
        acquisition_start_node = cast(ids_peak.CommandNode,
                                      nodemap_remote_device.FindNode("AcquisitionStart"))
        acquisition_start_node.Execute()
        acquisition_start_node.WaitUntilDone()

        for i in range(10):
            # Wait for the finished/filled buffer event.
            buffer = data_stream.WaitForFinishedBuffer(ids_peak.Timeout.INFINITE_TIMEOUT)

            if buffer.IsIncomplete():
                print(f"Image {i} is incomplete!")
                data_stream.QueueBuffer(buffer)
                continue

            image_view = buffer.ToImageView()

            image = Image.create_from_image_view(image_view)
            print("Captured image", i, image.metadata)

            data_stream.QueueBuffer(buffer)

        print("Stopping acquisition...")
        acquisition_stop_node = cast(ids_peak.CommandNode,
                                     nodemap_remote_device.FindNode("AcquisitionStop"))
        acquisition_stop_node.Execute()
        acquisition_stop_node.WaitUntilDone()
        data_stream.StopAcquisition(ids_peak.AcquisitionStopMode_Default)

        # Unlock writable nodes again. See `Lock writable nodes`.
        cast(ids_peak.IntegerNode, nodemap_remote_device.FindNode("TLParamsLocked")).SetValue(0)

        data_stream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)

        for buffer in data_stream.AnnouncedBuffers():
            # Remove buffer from the transport layer
            data_stream.RevokeBuffer(buffer)

    except Exception as e:
        print("Exception: " + str(e) + "")

    finally:
        # One call to `Close` is required for each call to `Initialize`.
        ids_peak.Library.Close()


if __name__ == "__main__":
    main()
