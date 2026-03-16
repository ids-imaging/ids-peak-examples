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
This example demonstrates how to handle device connection state changes
using the IDS peak reconnect feature. It also shows how to restore
the acquisition after a reconnect if configuration changes
(such as payload size) require buffer reallocation.

The application:
- Registers callbacks for device connection events
- Opens a device and starts image acquisition
- Enables the automatic reconnect feature
- Handles connection events during acquisition

The following events are reported through callbacks:

Disconnected:
    Device communication has been interrupted, but the transport layer
    can attempt to reconnect the device automatically.

Reconnected:
    The device was reconnected after a previous disconnect.

Lost:
    The device is no longer available and cannot be recovered automatically
    (for example if reconnect is disabled or a disconnected device has been closed).

Found:
    A new device was detected during a device discovery update.

"""

import sys
from typing import Optional

from ids_peak import ids_peak


class ReconnectExample:
    def __init__(self) -> None:
        # Initialize library, has to be matched by a Library.Close() call
        ids_peak.Library.Initialize()

        self.device_manager: ids_peak.DeviceManager = ids_peak.DeviceManager.Instance()
        self.acquisition_running: bool = False
        self.device: Optional[ids_peak.Device] = None
        self.remote_nodemap: Optional[ids_peak.NodeMap] = None
        self.data_stream: Optional[ids_peak.DataStream] = None

        self.register_callbacks()

    @staticmethod
    def device_found(device: ids_peak.DeviceDescriptor) -> None:
        """
        The 'found' event is triggered if a new device is found upon calling
        `DeviceManager.Update()`
        """
        print(f"Found-Device-Callback: Key={device.Key()}")

    @staticmethod
    def device_lost(key: str) -> None:
        """
        The 'lost' event is only called for this application's opened devices if
        a device is closed explicitly or if connection is lost while the reconnect is disabled,
        otherwise the 'disconnected' event is triggered.
        Other devices that were not opened or were opened by someone else still trigger
        a 'lost' event.
        """
        print(f"Lost-Device-Callback: Key={key}")

    def ensure_compatible_buffers_and_restart_acquisition(
            self, reconnect_information: ids_peak.DeviceReconnectInformation
            ) -> None:
        """
        After a reconnect the PayloadSize might have changed, e.g. due to
        a reboot and the last parameter state not being saved in the
        starting UserSet. Here we check the PayloadSize and
        reallocate the buffers if we encounter a mismatch.

        We also start the local and remote acquistion if necessary.
        """
        if self.remote_nodemap is None or self.data_stream is None:
            raise RuntimeError("Device is not opened!")

        payload_size = self.remote_nodemap.FindNode("PayloadSize").Value()

        has_payload_size_mismatch = payload_size != self.data_stream.AnnouncedBuffers()[0].Size()

        # The payload size might have changed. In this case it's required to reallocate the buffers.
        if has_payload_size_mismatch:
            print("PayloadSize has changed. Reallocating buffers...")

            is_data_stream_running = self.data_stream.IsGrabbing()
            if is_data_stream_running:
                self.data_stream.StopAcquisition()

            self.revoke_buffers()

            # Allocate and queue the buffers using the new "PayloadSize".
            self.alloc_buffers()

            if is_data_stream_running:
                self.data_stream.StartAcquisition()

        if not reconnect_information.IsRemoteDeviceAcquisitionRunning():
            self.remote_nodemap.FindNode("AcquisitionStart").Execute()

    def device_reconnected(
        self, device: ids_peak.Device, reconnect_information: ids_peak.DeviceReconnectInformation
    ) -> None:
        """
        When a device that was opened by the same application instance regains connection
        after a previous disconnect the 'Reconnected' event is triggered.

        The reconnect may (partially) fail, so we have to check the `DeviceReconnectInformation`
        class to know what steps are necessary to resume the acquistion.
        """
        print(
            (
                "Device-Reconnected-Callback:\n"
                f"Key={device.Key()}\n"
                f"ReconnectSuccessful: {reconnect_information.IsSuccessful()}\n"
                f"RemoteDeviceAcquisitionRunning: "
                f"{reconnect_information.IsRemoteDeviceAcquisitionRunning()}\n"
                f"RemoteDeviceConfigurationRestored: "
                f"{reconnect_information.IsRemoteDeviceConfigurationRestored()}"
            )
        )

        # Using the `reconnectInformation` the user can tell whether they need to take actions
        # in order to resume the image acquisition.
        if reconnect_information.IsSuccessful():
            # Device was reconnected successfully, nothing to do.
            return

        self.ensure_compatible_buffers_and_restart_acquisition(reconnect_information)

    @staticmethod
    def device_disconnected(device: ids_peak.DeviceDescriptor) -> None:
        """
        Only called if the reconnect is enabled and if the device was previously opened by this
        application instance.
        """
        print(f"Disconnected-Callback: Key={device.Key()}")

    def register_callbacks(self) -> None:
        """
        Register the Devicemanager callbacks.

        Note: We have to store the callbacks, otherwise the callbacks will
        be unregistered because their lifetime is shorter than the device manager instance.
        """
        # ids_peak provides several events that you can subscribe to in order
        # to be notified when the connection status of a device changes.
        self.device_found_callback = self.device_manager.DeviceFoundCallback(self.device_found)
        self.device_found_callback_handle = self.device_manager.RegisterDeviceFoundCallback(
                self.device_found_callback
                )

        self.device_lost_callback = self.device_manager.DeviceLostCallback(self.device_lost)
        self.device_lost_callback_handle = self.device_manager.RegisterDeviceLostCallback(
                self.device_lost_callback
                )

        self.device_reconnected_callback = self.device_manager.DeviceReconnectedCallback(
                self.device_reconnected
                )
        self.device_reconnected_callback_handle = (
                self.device_manager.RegisterDeviceReconnectedCallback(
                    self.device_reconnected_callback)
                )

        self.device_disconnected_callback = self.device_manager.DeviceDisconnectedCallback(
                self.device_disconnected
                )
        self.device_disconnected_callback_handle = (
                self.device_manager.RegisterDeviceDisconnectedCallback(
                    self.device_disconnected_callback
                    )
                )

    def unregister_callbacks(self) -> None:
        """
        Unregister the registered callbacks inside the Devicemanager
        """
        self.device_manager.UnregisterDeviceFoundCallback(self.device_found_callback_handle)
        self.device_manager.UnregisterDeviceLostCallback(self.device_lost_callback_handle)
        self.device_manager.UnregisterDeviceReconnectedCallback(
                self.device_reconnected_callback_handle
                )
        self.device_manager.UnregisterDeviceDisconnectedCallback(
                self.device_disconnected_callback_handle
                )

    def run_acquisition_loop(self) -> None:
        """
        Run the acquisition loop. The reconnect callback may abort this.
        """

        if self.remote_nodemap is None or self.data_stream is None:
            raise RuntimeError("Device is not opened!")

        # Lock writable nodes, which could influence the payload size or
        # similar information during acquisition.
        self.remote_nodemap.FindNode("TLParamsLocked").SetValue(1)

        self.data_stream.StartAcquisition()
        self.remote_nodemap.FindNode("AcquisitionStart").Execute()
        self.remote_nodemap.FindNode("AcquisitionStart").WaitUntilDone()

        self.acquisition_running = True
        print("Starting acquisition...")
        print("Now you can disconnect or reboot the device to trigger a reconnect!")
        while self.acquisition_running:
            try:
                # Wait for the finished/filled buffer event.
                buffer = self.data_stream.WaitForFinishedBuffer(ids_peak.Timeout.INFINITE_TIMEOUT)
                print(f"Received FrameID: {buffer.FrameID()}")
                # Put the buffer back in the pool, so it can be filled again.
                self.data_stream.QueueBuffer(buffer)
            except KeyboardInterrupt:
                print("Keyboard interrupt.")
                break
            except Exception as e:
                print(f"Exception: {e}")

        print("Stopping acquisition...")
        self.remote_nodemap.FindNode("AcquisitionStop").Execute()
        self.remote_nodemap.FindNode("AcquisitionStop").WaitUntilDone()
        self.data_stream.StopAcquisition(ids_peak.AcquisitionStopMode_Default)

        # Unlock writable nodes again. See `Lock writable nodes`.
        self.remote_nodemap.FindNode("TLParamsLocked").SetValue(0)

    def open_device(self) -> None:
        # Open the first openable device.
        device = None
        for dev in self.device_manager.Devices():
            if dev.IsOpenable(ids_peak.DeviceAccessType_Control):
                device = dev.OpenDevice(ids_peak.DeviceAccessType_Control)

        # Exit the program if no device was found.
        if not device:
            raise RuntimeError("No device found. Exiting Program.")

        self.device = device

        print("Using Device " + self.device.DisplayName())
        # Retrieve the remote device's primary node map.
        # In GenICam, a node map represents a hierarchical set of parameters (features)
        # such as exposure, gain, and firmware info. The node map provides access to controls
        # implemented on the device itself, typically following the GenICam SFNC,
        # while allowing for device-specific extensions.
        self.remote_nodemap = self.device.RemoteDevice().NodeMaps()[0]
        self.data_stream = self.device.DataStreams()[0].OpenDataStream()

    def enable_reconnect(self) -> None:
        """
        We enable the reconnect by writing to the `ReconnectEnable` node
        in the `NodeMap` of the `System` that our device is connected to.
        """

        if self.device is None:
            raise RuntimeError("Device is not opened!")

        system_node_map = self.device.ParentInterface().ParentSystem().NodeMaps()[0]

        if not system_node_map.HasNode("ReconnectEnable"):
            raise RuntimeError("No ReconnectEnable Node found!")

        reconnect_enable_node = system_node_map.FindNode("ReconnectEnable")
        reconnect_enable_access_status = reconnect_enable_node.AccessStatus()

        if reconnect_enable_access_status == ids_peak.NodeAccessStatus_ReadWrite:
            reconnect_enable_node.SetValue(True)
            return

        if reconnect_enable_access_status == ids_peak.NodeAccessStatus_ReadOnly:
            if reconnect_enable_node.Value():
                return

        raise RuntimeError("Error: ReconnectEnable cannot be set to true!")

    def load_defaults(self) -> None:

        if self.remote_nodemap is None:
            raise RuntimeError("Device is not opened!")

        self.remote_nodemap.FindNode("UserSetSelector").SetCurrentEntry("Default")
        self.remote_nodemap.FindNode("UserSetLoad").Execute()
        self.remote_nodemap.FindNode("UserSetLoad").WaitUntilDone()

    def alloc_buffers(self) -> None:
        if self.remote_nodemap is None or self.data_stream is None:
            raise RuntimeError("Device is not opened!")

        # Buffer size
        payload_size = self.remote_nodemap.FindNode("PayloadSize").Value()

        # Minimum number of required buffers
        buffer_count_max = self.data_stream.NumBuffersAnnouncedMinRequired()

        # Allocate buffers and add them to the pool
        for _ in range(buffer_count_max):
            # Let the TL allocate the buffers
            buffer = self.data_stream.AllocAndAnnounceBuffer(payload_size)
            # Put the buffer in the pool
            self.data_stream.QueueBuffer(buffer)

    def revoke_buffers(self) -> None:
        if self.data_stream is None:
            raise RuntimeError("Device is not opened!")

        # Remove buffers from any associated queue
        self.data_stream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)

        for buffer in self.data_stream.AnnouncedBuffers():
            # Remove buffer from the transport layer
            self.data_stream.RevokeBuffer(buffer)

    def set_roi(self) -> None:
        if self.remote_nodemap is None:
            raise RuntimeError("Device is not opened!")

        # In order to restart the acquistion additonal steps are required:
        # see "The payload size might have changed." above.
        self.remote_nodemap.FindNode("Height").SetValue(512)
        self.remote_nodemap.FindNode("Width").SetValue(512)

    def run(self) -> None:
        try:
            # Update the DeviceManager.
            # When `Update` is called, it searches for all producer libraries
            # contained in the directories found in the official GenICam GenTL
            # environment variable GENICAM_GENTL{32/64}_PATH. It then opens all
            # found ProducerLibraries, their Systems, their Interfaces, and lists
            # all available DeviceDescriptors.
            ids_peak.DeviceManager.Instance().Update()

            # Open the first available device.
            self.open_device()

            # Enable the reconnect feature.
            self.enable_reconnect()

            # Load default camera settings.
            self.load_defaults()

            # NOTE: Uncommenting this line will modify the PayloadSize without saving the
            # changes in the UserSet. If the device reboots (e.g. by losing and then regaining
            # power) the PayloadSize will have changed, which means the acquisition on
            # the remote device will not be restarted.
            # self.set_roi()

            # Allocate buffers for the acquisition.
            self.alloc_buffers()

            # Run acquisition loop until an error occurs or the user presses Ctrl+C.
            self.run_acquisition_loop()

            # Revoke all buffers.
            self.revoke_buffers()

        except ids_peak.AbortedException:
            print("Aborted")
        except Exception as e:
            print("EXCEPTION: " + str(e))
            sys.exit(-2)

        finally:
            self.unregister_callbacks()
            ids_peak.Library.Close()


if __name__ == "__main__":
    example = ReconnectExample()
    example.run()
