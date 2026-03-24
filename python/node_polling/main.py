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

"""
This example demonstrates how node polling is used to regularly
invalidate GenICam nodes that implement the PollingTime feature,
ensuring that cached values stay up to date.

The application:
- Initializes the IDS peak library
- Detects and opens the first available device
- Prepares and starts image acquisition
- Starts a background thread to periodically poll the nodes
- Enables automatic exposure control (ExposureAuto = Continuous)
- Continuously reads and prints the current exposure time along with
  polling statistics

By polling the node map, nodes with a defined PollingTime are
invalidated automatically once their polling interval elapses.
This guarantees that subsequent reads (e.g., ExposureTime during
auto exposure) return values from the device instead of
cached data.
"""

import time
import signal
from types import FrameType
from typing import cast, Optional
from threading import Thread

from ids_peak import ids_peak


class NodePollingExample:
    def __init__(self) -> None:
        self._device_manager = ids_peak.DeviceManager.Instance()
        self._should_stop: bool = False

        self._device: ids_peak.Device = self._open_first_available_camera()
        self._datastream = self._device.DataStreams()[0].OpenDataStream()
        self._remote_device_node_map: ids_peak.NodeMap = self._device.RemoteDevice().NodeMaps()[0]

        self._polling_thread = Thread(target=self._poll_nodes)
        self._times_polled: int = 0

        self._check_camera_compatibility()

        self._exposure_time_node = cast(ids_peak.FloatNode,
                                        self._remote_device_node_map.FindNode("ExposureTime"))

    def _open_first_available_camera(self) -> ids_peak.Device:
        # Update the device manager.
        # When `Update` is called, it searches for all producer libraries
        # contained in the directories found in the official GenICam GenTL
        # environment variable GENICAM_GENTL{32/64}_PATH. It then opens all
        # found ProducerLibraries, their Systems, their Interfaces, and lists
        # all available DeviceDescriptors.
        self._device_manager.Update()

        # Exit program if no device was found.
        if len(self._device_manager.Devices()) == 0:
            raise RuntimeError("No devices found. Exiting Program.")

        target_device_descriptor: ids_peak.DeviceDescriptor | None = None

        for device in self._device_manager.Devices():
            if not device.IsOpenable():
                continue
            target_device_descriptor = device
            break

        if not target_device_descriptor:
            raise RuntimeError("No openable device found. Exiting Program.")

        # Open the first available device with control access.
        return target_device_descriptor.OpenDevice(ids_peak.DeviceAccessType_Control)

    def _check_camera_compatibility(self) -> None:
        """
        Check whether the connected camera is compatible with this example.
        """
        for node_name in ["ExposureTime", "ExposureAuto"]:
            if not self._remote_device_node_map.HasNode(node_name):
                raise RuntimeError(f"Cannot run example: Node {node_name} "
                                   f"is not found in remote node map!")

        node = self._remote_device_node_map.FindNode("ExposureAuto")
        access_status = node.AccessStatus()
        if access_status is not ids_peak.NodeAccessStatus_ReadWrite:
            raise RuntimeError("Cannot run example: Node ExposureAuto is not writable!")

    def _poll_nodes(self) -> None:
        """
        Periodically polls all registered nodes to manage their cache validity.

        Each node may define its own polling interval (PollingTime). If the
        accumulated elapsed time exceeds a node's PollingTime, the node is
        invalidated. This ensures that the next read operation fetches
        data directly from the device instead of returning cached values.
        """
        interval_ms = 500
        start = time.time()
        while not self._should_stop:
            time.sleep(interval_ms / 1000)

            now = time.time()
            elapsed = now - start
            start = now

            self._remote_device_node_map.PollNodes(int(elapsed * 1000))
            self._times_polled += 1

    def _prepare_acquisition(self) -> None:
        """
        Allocate minimum amount of required buffers and add them to the buffer queue.
        """
        num_buffers_required = self._datastream.NumBuffersAnnouncedMinRequired()
        if self._datastream.DefinesPayloadSize():
            payload_size: int = self._datastream.PayloadSize()
        else:
            payload_size = cast(ids_peak.IntegerNode,
                                self._remote_device_node_map.FindNode("PayloadSize")).Value()

        for _ in range(num_buffers_required):
            buffer = self._datastream.AllocAndAnnounceBuffer(payload_size)
            self._datastream.QueueBuffer(buffer)

    def run(self) -> None:
        print("Press Ctrl+C to stop this example!")

        # Automatic exposure adjustment requires image acquisition.
        # For U3V cameras, the data stream must be started before initiating remote acquisition.
        self._prepare_acquisition()
        self._datastream.StartAcquisition()
        acquisition_start_node = cast(ids_peak.CommandNode,
                                      self._remote_device_node_map.FindNode("AcquisitionStart"))
        acquisition_start_node.Execute()
        acquisition_start_node.WaitUntilDone()

        # Start the polling thread
        self._polling_thread.start()

        # Enable the ExposureAuto node
        exposure_auto_node = cast(ids_peak.EnumerationNode,
                                  self._remote_device_node_map.FindNode("ExposureAuto"))
        exposure_auto_node.SetCurrentEntry("Continuous")

        # Continuously read the exposure time and print statistics
        while not self._should_stop:
            if self._exposure_time_node is not None:
                exposure_time = self._exposure_time_node.Value()
                print(f"\rTimes polled: {self._times_polled:3}, "
                      f"Current exposure time: {exposure_time:.2f} us.", end="")
            time.sleep(0.1)

    def stop(self) -> None:
        """
        Sets a stop flag to tell the main loop and the polling thread to stop.
        """
        self._should_stop = True
        self._polling_thread.join()


if __name__ == "__main__":
    # The library must be initialized before use.
    # Each `Initialize` call must be matched with a corresponding call
    # to `Close`.
    ids_peak.Library.Initialize()

    try:
        example = NodePollingExample()


        def handle_sigint(signum: int, frame: Optional[FrameType]) -> None:
            example.stop()


        signal.signal(signal.SIGINT, handle_sigint)

        example.run()
    except Exception as e:
        print(f"Error: {e}")

    finally:
        # One call to `Close` is required for each call to `Initialize`.
        ids_peak.Library.Close()
