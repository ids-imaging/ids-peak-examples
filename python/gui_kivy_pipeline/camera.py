# Copyright (C) 2025, IDS Imaging Development Systems GmbH.
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

from ids_peak_afl import ids_peak_afl
from ids_peak_common import Range, PixelFormat, CommonException, Channel
from ids_peak import ids_peak, ImageView
from ids_peak.ids_peak import (
    Device,
    NodeMap,
    DataStream,
    Buffer,
    Timeout,
    DataStreamFlushMode_DiscardAll,
    AcquisitionStopMode_Default,
)


class Camera:
    def __init__(self) -> None:
        # Initialize global library instances before interacting with any devices.
        # Each initialization must later be paired with the appropriate cleanup call.
        ids_peak.Library.Initialize()
        ids_peak_afl.Library.Init()

        # Query and update the device manager to discover connected devices
        # according to the GenICam/GentL producer environment configuration.
        instance = ids_peak.DeviceManager.Instance()
        instance.Update()

        # Create a list with all openable devices.
        devices = list(
            filter(
                lambda dev: dev.IsOpenable(ids_peak.DeviceAccessType_Control),
                instance.Devices(),
            )
        )

        # Terminate early if no device is available for control access.
        if len(devices) == 0:
            print("No available camera connected")
            raise SystemExit("Failed to open camera")

        # Open the first available device with control access.
        self._device = devices[0].OpenDevice(ids_peak.DeviceAccessType_Control)

        # Open the primary data stream which handles buffer allocation,
        # queuing, and reception of image data from the transport layer.
        self._data_stream: DataStream = self._device.DataStreams()[0].OpenDataStream()

        # Access the device's remote node map — the standardized GenICam feature tree
        # that exposes camera controls such as exposure, gain, pixel format, frame rate, etc.
        self._remote_node_map: NodeMap = self._device.RemoteDevice().NodeMaps()[0]

        self._acquisition_running = False

        # Do not allow these packed formats
        if self.pixel_format in [PixelFormat.RGB_10_PACKED_32, PixelFormat.BGR_10_PACKED_32]:
            try:
                self.pixel_format = list(
                    filter(lambda x: x.has_channel(Channel.BAYER), self.pixel_format_list)
                )[0]
            except CommonException as e:
                print(e)

        # Fix the coordinate system for kivy
        self.fix_coordinates()

        # Disable device auto features in order to use the pipeline
        # host auto features. Otherwise, certain nodes, like e.g., 'Gain'
        # would not be writable.
        self.disable_device_autofeatures()

        # Try to enable the reconnect feature if it is supported
        try:
            system_node_map = self.device.ParentInterface().ParentSystem().NodeMaps()[0]
            reconnect_enable_node = cast(
                ids_peak.BooleanNode | None, system_node_map.TryFindNode("ReconnectEnable")
            )
            if reconnect_enable_node is not None:
                reconnect_enable_node.SetValue(True)
        except CommonException:
            pass

        # Add reconnect handler
        self.device_reconnected_callback = instance.DeviceReconnectedCallback(
            self.device_reconnected
        )
        self.device_reconnected_callback_handle = instance.RegisterDeviceReconnectedCallback(
            self.device_reconnected_callback
        )

    def __del__(self) -> None:
        ids_peak.Library.Close()
        ids_peak_afl.Library.Exit()

    def device_reconnected(
        self,
        device: ids_peak.Device,
        reconnect_information: ids_peak.DeviceReconnectInformation,
    ) -> None:
        # Using the `DeviceReconnectInformation` the user can tell whether they need to take actions
        # in order to resume the image acquisition.

        print("Device reconnected!")

        # Check if the automatic reconnect was already successful
        if reconnect_information.IsSuccessful():
            # Restore ReverseY because user set loading may override orientation.
            self.fix_coordinates()
            # Disable device auto features, since the settings might have
            # change after e.g., a reboot due to a power loss.
            self.disable_device_autofeatures()

            # The Device was reconnected successfully, nothing else to do.
            return

        payload_size = cast(
            ids_peak.IntegerNode,
            self.remote_device_nodemap.FindNode("PayloadSize"),
        ).Value()

        has_payload_size_mismatch = payload_size != self.data_stream.AnnouncedBuffers()[0].Size()

        # The payload size might have changed.
        # In this case, it's required to reallocate the buffers.
        if has_payload_size_mismatch:
            self.stop_acquisition()
            self.fix_coordinates()
            self.disable_device_autofeatures()
            self.start_acquisition()
        elif not reconnect_information.IsRemoteDeviceAcquisitionRunning():
            cast(
                ids_peak.CommandNode, self.remote_device_nodemap.FindNode("AcquisitionStart")
            ).Execute()

    def fix_coordinates(self) -> None:
        # Kivy and OpenGL have flipped coordinate systems compared to the image,
        # so we mirror the image vertically to display it upright again.
        node = cast(ids_peak.BooleanNode | None, self.remote_device_nodemap.TryFindNode("ReverseY"))

        # Only modify this node if it is writable (depends on the device state or userset).
        try:
            if node is not None and node.IsAvailable():
                if not node.IsWriteable():
                    was_started = self.acquisition_running
                    if was_started:
                        self.stop_acquisition()
                    node.SetValue(True)
                    if was_started:
                        self.start_acquisition()
                else:
                    node.SetValue(True)
        except CommonException:
            pass

    def disable_device_autofeatures(self) -> None:
        auto_node_names = ["ExposureAuto", "BalanceWhiteAuto", "GainAuto", "FocusAuto"]

        for node_name in auto_node_names:
            node = cast(
                ids_peak.EnumerationNode | None,
                self.remote_device_nodemap.TryFindNode(node_name),
            )

            try:
                if node is not None:
                    node.SetCurrentEntry("Off")
            except CommonException:
                pass

    def restore_coordinate_flip(self) -> None:
        node = cast(ids_peak.BooleanNode | None, self.remote_device_nodemap.TryFindNode("ReverseY"))
        try:
            if node is not None and node.IsWriteable():
                node.SetValue(False)
        except CommonException:
            pass

    def start_acquisition(self) -> None:
        if self.acquisition_running:
            return

        # Get the payload size, which determines our buffer size.
        payload_size = cast(
            ids_peak.IntegerNode, self.remote_device_nodemap.FindNode("PayloadSize")
        ).Value()

        # The transport layer requires a minimum number of buffers to be announced.
        # A larger amount of buffers may improve stability.
        buffer_count_max = self.data_stream.NumBuffersAnnouncedMinRequired()
        for _ in range(buffer_count_max):
            # Let the transport layer allocate the buffers for easier memory management.
            buffer = self.data_stream.AllocAndAnnounceBuffer(payload_size)
            # Queue the buffer so that the datastream is allowed to fill it with image data.
            self.data_stream.QueueBuffer(buffer)

        # Lock nodes that may affect payload size or transport configuration.
        # During acquisition, these parameters must remain unchanged or the
        # announced buffers may become mismatched.
        cast(ids_peak.IntegerNode, self.remote_device_nodemap.FindNode("TLParamsLocked")).SetValue(
            1
        )

        print("Starting acquisition...")
        self._acquisition_running = True

        # Start both host-side and device-side acquisition.
        self.data_stream.StartAcquisition()
        cast(
            ids_peak.CommandNode, self.remote_device_nodemap.FindNode("AcquisitionStart")
        ).Execute()
        cast(
            ids_peak.CommandNode, self.remote_device_nodemap.FindNode("AcquisitionStart")
        ).WaitUntilDone()

    def stop_acquisition(self) -> None:
        if not self._acquisition_running:
            return

        print("Stopping acquisition...")

        self._acquisition_running = False

        # Stopping the remote acquisition should occur before stopping the
        # data stream to avoid leaving (partially) filled buffers in the datastream.
        cast(ids_peak.CommandNode, self.remote_device_nodemap.FindNode("AcquisitionStop")).Execute()
        cast(
            ids_peak.CommandNode, self.remote_device_nodemap.FindNode("AcquisitionStop")
        ).WaitUntilDone()

        # Stop host-side acquisition and flush any in-flight buffers.
        # DiscardAll ensures no old buffers are reused after a configuration change.
        if self.data_stream.IsGrabbing():
            self.data_stream.StopAcquisition(AcquisitionStopMode_Default)
        self.data_stream.Flush(DataStreamFlushMode_DiscardAll)

        # Revoke announced buffers after stopping acquisition because
        # settings that influence the payload size might change
        # before starting the acquisition.
        for buffer in self.data_stream.AnnouncedBuffers():
            self.data_stream.RevokeBuffer(buffer)

        # Unlock parameters again, now that acquisition has stopped.
        cast(ids_peak.IntegerNode, self.remote_device_nodemap.FindNode("TLParamsLocked")).SetValue(
            0
        )

    def kill_datastream_wait(self) -> None:
        # To let a waiting WaitForFinishedBuffer return, we need to send it a kill signal
        self.data_stream.KillWait()

    def wait_for_image_view(self, timeout: int = 5000) -> ImageView:
        # Wait for the next finished buffer.
        # Using Timeout ensures that acquisition stalls
        # (due to disconnections or timeouts) do not
        # block the calling thread indefinitely.
        buffer = self.data_stream.WaitForFinishedBuffer(Timeout(timeout))

        # Convert to an ImageView which provides a lightweight GenICam-style
        # pixel memory representation without taking ownership of the buffer.
        return buffer.ToImageView()

    def queue_buffer(self, buffer: Buffer) -> None:
        # Queue the buffer back to the acquisition engine so it can be reused.
        # This must be done after every call to WaitForFinishedBuffer.
        self.data_stream.QueueBuffer(buffer)

    @property
    def device(self) -> Device:
        return self._device

    @property
    def remote_device_nodemap(self) -> NodeMap:
        return self._remote_node_map

    @property
    def data_stream(self) -> DataStream:
        return self._data_stream

    @property
    def acquisition_running(self) -> bool:
        return self._acquisition_running

    def _range_from_node(self, node_name: str) -> Range:
        node = cast(
            ids_peak.IntegerNode | ids_peak.FloatNode,
            self.remote_device_nodemap.FindNode(node_name),
        )
        increment_type = node.IncrementType()
        node_type = node.Type()
        if increment_type == ids_peak.NodeIncrementType_NoIncrement:
            return Range(
                node.Minimum(),
                node.Maximum(),
                0.0 if node_type is ids_peak.NodeType_Float else 0,
            )
        elif increment_type == ids_peak.NodeIncrementType_FixedIncrement:
            return Range(node.Minimum(), node.Maximum(), node.Increment())
        else:
            raise ValueError("Node has no supported increment")

    @property
    def pixel_format(self) -> PixelFormat:
        # PixelFormat is a selector node.
        # The active entry determines how the
        # device internally formats the image data before transmission.
        return PixelFormat.create_from_string_value(
            cast(ids_peak.EnumerationNode, self.remote_device_nodemap.FindNode("PixelFormat"))
            .CurrentEntry()
            .SymbolicValue()
        )

    @pixel_format.setter
    def pixel_format(self, pixel_format: PixelFormat) -> None:
        # Pixel format changes can alter payload size — acquisition must be stopped first.
        was_running = self._acquisition_running
        if was_running:
            self.stop_acquisition()
        cast(
            ids_peak.EnumerationNode, self.remote_device_nodemap.FindNode("PixelFormat")
        ).SetCurrentEntry(pixel_format.string_value)
        if was_running:
            self.start_acquisition()

    @property
    def pixel_format_list(self) -> list[PixelFormat]:
        # Enumerate all symbolic entries supported by the device.
        # Not all entries returned by `Entries` are guaranteed to be valid.
        # Use `AvailableEntries` to get a filtered list.
        pixel_format = cast(
            ids_peak.EnumerationNode, self.remote_device_nodemap.FindNode("PixelFormat")
        )
        entries = pixel_format.AvailableEntries()
        return [
            PixelFormat.create_from_string_value(entry.SymbolicValue())
            for entry in entries
            if PixelFormat.create_from_string_value(entry.SymbolicValue())
            not in [PixelFormat.RGB_10_PACKED_32, PixelFormat.BGR_10_PACKED_32]
        ]

    @property
    def exposure(self) -> float:
        value = cast(
            ids_peak.FloatNode, self.remote_device_nodemap.FindNode("ExposureTime")
        ).Value()
        return cast(float, value)

    @exposure.setter
    def exposure(self, exposure: float) -> None:
        cast(ids_peak.FloatNode, self.remote_device_nodemap.FindNode("ExposureTime")).SetValue(
            float(exposure)
        )

    @property
    def exposure_range(self) -> Range:
        return self._range_from_node("ExposureTime")

    @property
    def framerate(self) -> float:
        # Reading the frame rate does not guarantee that the device can
        # actually *deliver* this rate; it depends on exposure, ROI, bandwidth, etc.
        value = cast(
            ids_peak.FloatNode, self.remote_device_nodemap.FindNode("AcquisitionFrameRate")
        ).Value()
        return cast(float, value)

    @framerate.setter
    def framerate(self, frame_rate: float) -> None:
        cast(
            ids_peak.FloatNode, self.remote_device_nodemap.FindNode("AcquisitionFrameRate")
        ).SetValue(float(frame_rate))

    @property
    def framerate_range(self) -> Range:
        return self._range_from_node("AcquisitionFrameRate")

    @property
    def has_focus_stepper(self) -> bool:
        node = cast(
            ids_peak.IntegerNode | None,
            self.remote_device_nodemap.TryFindNode("FocusStepper"),
        )
        if not node:
            return False
        return cast(bool, node.IsAvailable())

    @property
    def focus_stepper(self) -> int:
        value = cast(
            ids_peak.IntegerNode, self.remote_device_nodemap.FindNode("FocusStepper")
        ).Value()

        return cast(int, value)

    @focus_stepper.setter
    def focus_stepper(self, value: int) -> None:
        cast(ids_peak.IntegerNode, self.remote_device_nodemap.FindNode("FocusStepper")).SetValue(
            value
        )

    @property
    def focus_stepper_range(self) -> Range:
        return self._range_from_node("FocusStepper")

    def _set_gain_selector(self, gain_type: str) -> None:
        # Gain is typically controlled through a selector node.
        # Some devices expose multiple selector prefixes (Analog/Digital)
        # or only one of the variants and require selecting a
        # specific preferred entry before accessing Gain.
        preferred_selector_prefix = ["Analog", "Digital", ""]
        preferred_selector = [prefix + gain_type for prefix in preferred_selector_prefix]

        gain_selector = cast(
            ids_peak.EnumerationNode | None,
            self.remote_device_nodemap.TryFindNode("GainSelector"),
        )
        if gain_selector is None or not gain_selector.IsAvailable():
            return

        entries = gain_selector.AvailableEntries()

        # Pick the first matching entry respecting the preferred order.
        supported = filter(lambda entry: entry.SymbolicValue() in preferred_selector, entries)
        gain_selector.SetCurrentEntry(next(supported))

    @property
    def master_gain(self) -> float:
        self._set_gain_selector("All")
        value = cast(ids_peak.FloatNode, self.remote_device_nodemap.FindNode("Gain")).Value()
        return cast(float, value)

    @master_gain.setter
    def master_gain(self, value: float) -> None:
        self._set_gain_selector("All")
        cast(ids_peak.FloatNode, self.remote_device_nodemap.FindNode("Gain")).SetValue(value)

    @property
    def master_gain_range(self) -> Range:
        self._set_gain_selector("All")
        return self._range_from_node("Gain")

    @property
    def red_gain(self) -> float:
        self._set_gain_selector("Red")
        value = cast(ids_peak.FloatNode, self.remote_device_nodemap.FindNode("Gain")).Value()
        return cast(float, value)

    @red_gain.setter
    def red_gain(self, value: float) -> None:
        self._set_gain_selector("Red")
        cast(ids_peak.FloatNode, self.remote_device_nodemap.FindNode("Gain")).SetValue(value)

    @property
    def red_gain_range(self) -> Range:
        self._set_gain_selector("Red")
        return self._range_from_node("Gain")

    @property
    def green_gain(self) -> float:
        self._set_gain_selector("Green")
        value = cast(ids_peak.FloatNode, self.remote_device_nodemap.FindNode("Gain")).Value()
        return cast(float, value)

    @green_gain.setter
    def green_gain(self, value: float) -> None:
        self._set_gain_selector("Green")
        cast(ids_peak.FloatNode, self.remote_device_nodemap.FindNode("Gain")).SetValue(value)

    @property
    def green_gain_range(self) -> Range:
        self._set_gain_selector("Green")
        return self._range_from_node("Gain")

    @property
    def blue_gain(self) -> float:
        self._set_gain_selector("Blue")
        value = cast(ids_peak.FloatNode, self.remote_device_nodemap.FindNode("Gain")).Value()
        return cast(float, value)

    @blue_gain.setter
    def blue_gain(self, value: float) -> None:
        self._set_gain_selector("Blue")
        cast(ids_peak.FloatNode, self.remote_device_nodemap.FindNode("Gain")).SetValue(value)

    @property
    def blue_gain_range(self) -> Range:
        self._set_gain_selector("Blue")
        return self._range_from_node("Gain")

    def gain_type_list(self) -> list[str]:
        gain_selector_node = cast(
            ids_peak.EnumerationNode, self.remote_device_nodemap.FindNode("GainSelector")
        )
        return [entry.SymbolicValue() for entry in gain_selector_node.AvailableEntries()]

    def set_gain(self, gain_type: str, gain: float) -> None:
        cast(
            ids_peak.EnumerationNode, self.remote_device_nodemap.FindNode("GainSelector")
        ).SetCurrentEntry(gain_type)
        cast(ids_peak.FloatNode, self.remote_device_nodemap.FindNode("Gain")).SetValue(float(gain))

    def get_gain(self, gain_type: str) -> tuple[float, Range]:
        cast(
            ids_peak.EnumerationNode, self.remote_device_nodemap.FindNode("GainSelector")
        ).SetCurrentEntry(gain_type)
        gain_node = cast(ids_peak.FloatNode, self.remote_device_nodemap.FindNode("Gain"))
        return gain_node.Value(), self._range_from_node("Gain")

    def reset_to_default(self) -> None:
        # Loading the user set requires stopping the acquisition because
        # the device will be reconfigured.
        self.stop_acquisition()

        # Loading the “Default” user set resets most parameters
        # to factory or integrator-defined values.
        cast(
            ids_peak.EnumerationNode, self.remote_device_nodemap.FindNode("UserSetSelector")
        ).SetCurrentEntry("Default")
        cast(ids_peak.CommandNode, self.remote_device_nodemap.FindNode("UserSetLoad")).Execute()

        # Restore ReverseY because user set loading may override orientation.
        self.fix_coordinates()

        # Disable device auto features, since the settings might have
        # change after e.g., a reboot due to a power loss.
        self.disable_device_autofeatures()

        # Acquisition can now be restarted.
        self.start_acquisition()
