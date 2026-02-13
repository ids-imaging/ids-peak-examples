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

from __future__ import annotations

from enum import IntEnum
from typing import Sequence, Callable, TypeAlias, cast

from ids_peak import ids_peak
from ids_peak import exceptions as ids_peak_exceptions


class AcquisitionMode(IntEnum):
    """Camera image acquisition modes."""
    UNKNOWN = -1
    FREERUN = 0
    SOFTWARE_TRIGGER = 1

    def __str__(self) -> str:
        return self.name


class NodeMapType(IntEnum):
    """Node map types."""
    REMOTE_DEVICE = 0
    LOCAL_DEVICE = 1
    DATASTREAM = 2
    INTERFACE = 3
    SYSTEM = 4

    def __str__(self) -> str:
        return self.name


class UserSet(IntEnum):
    """Camera UserSets."""
    DEFAULT = 0
    HIGH_SPEED = 1
    LINESCAN = 2
    LINESCAN_HIGH_SPEED = 3
    LONG_EXPOSURE = 4
    USER_SET_0 = 5
    USER_SET_1 = 6
    QUAD_HDR = 7
    CLEAR_HDR = 8

    def __str__(self) -> str:
        return self.name

    @property
    def selector_value(self) -> str:
        """Return the selector string corresponding to this UserSet."""
        _selector_map = {
            UserSet.DEFAULT: "Default",
            UserSet.HIGH_SPEED: "HighSpeed",
            UserSet.LINESCAN: "Linescan",
            UserSet.LINESCAN_HIGH_SPEED: "LinescanHighSpeed",
            UserSet.LONG_EXPOSURE: "LongExposure",
            UserSet.USER_SET_0: "UserSet0",
            UserSet.USER_SET_1: "UserSet1",
            UserSet.QUAD_HDR: "QuadHDR",
            UserSet.CLEAR_HDR: "ClearHDR",
        }

        try:
            return _selector_map[self]
        except KeyError as exc:
            raise KeyError(f"Unknown UserSet value: {self.value}") from exc


_frame_start_trigger_entries = [
    "ExposureStart",
    "FrameStart",
    "ReadOutStart",
]

_DeviceFilter: TypeAlias = Callable[
    [ids_peak.DeviceDescriptor], bool]


class Camera:
    """Wraps a device object to expose additional camera-specific features."""

    def __init__(self, device: ids_peak.Device) -> None:
        self._acquisition_frame_count = ids_peak.DataStream.INFINITE_NUMBER
        self._acquisition_mode = AcquisitionMode.UNKNOWN
        self._device: ids_peak.Device | None = device
        try:
            self._data_stream = self._device.DataStreams()[
                0].OpenedDataStream()
        except ids_peak_exceptions.Exception:
            self._data_stream = self._device.DataStreams()[0].OpenDataStream()

        self._node_maps: dict[NodeMapType, ids_peak.NodeMap] = {
            NodeMapType.REMOTE_DEVICE: self._device.RemoteDevice().NodeMaps()[
                0],
            NodeMapType.LOCAL_DEVICE: self._device.NodeMaps()[0],
            NodeMapType.DATASTREAM: self._data_stream.NodeMaps()[0],
            NodeMapType.INTERFACE: self._device.ParentInterface().NodeMaps()[
                0],
            NodeMapType.SYSTEM:
                self._device.ParentInterface().ParentSystem().NodeMaps()[0],
        }

        self._update_acquisition_mode()

    @classmethod
    def open_first_available(cls) -> Camera:
        """Open first available camera."""
        return cls._open_with_condition(lambda _: True)

    @classmethod
    def open_by_serial_number(cls, serial_number: str) -> Camera:
        """Open camera by serial number."""

        def serial_filter(device: ids_peak.DeviceDescriptor) -> bool:
            return device.SerialNumber() == serial_number

        return cls._open_with_condition(serial_filter)

    @classmethod
    def _open_with_condition(cls, condition: _DeviceFilter) -> Camera:
        device_manager = ids_peak.DeviceManager.Instance()
        device_manager.Update()
        devices = device_manager.Devices()
        if len(devices) == 0:
            raise RuntimeError("No devices found")

        selected_device: ids_peak.DeviceDescriptor | None = None
        access_type = ids_peak.DeviceAccessType_Control
        for device in devices:
            if condition(device) and device.IsOpenable(access_type):
                selected_device = device
                break
        if selected_device is None:
            raise RuntimeError("No available device found")

        return cls(selected_device.OpenDevice(access_type))

    def has_node(
            self, node_name: str,
            node_map_type: NodeMapType = NodeMapType.REMOTE_DEVICE) -> bool:
        """Return True if a node with the given name exists."""
        node_map = self._node_maps[node_map_type]
        return node_map.HasNode(node_name)

    def has_nodes(
            self, node_names: Sequence[str],
            node_map_type: NodeMapType = NodeMapType.REMOTE_DEVICE) -> bool:
        """Return True if all nodes in the given list exist."""
        return all(self.has_node(node, node_map_type) for node in node_names)

    def has_enum_node_entry(
            self, node_name: str, entry_name: str,
            node_map_type: NodeMapType = NodeMapType.REMOTE_DEVICE) -> bool:
        """Check if the specified enumeration node contains the given entry."""
        node = cast(ids_peak.EnumerationNode,
                    self._node_maps[node_map_type].FindNode(node_name))
        entry_node = node.TryFindEntry(entry_name)
        return entry_node is not None and entry_node.IsAvailable()

    def set_enum_node_entry(
            self, node_name: str, entry_name: str,
            node_map_type: NodeMapType = NodeMapType.REMOTE_DEVICE) -> None:
        """Assign the given entry to the specified enumeration node."""
        node = cast(ids_peak.EnumerationNode,
                    self._node_maps[node_map_type].FindNode(node_name))
        node.SetCurrentEntry(entry_name)

    def set_node_value(
            self, node_name: str, value: str | bool | int | float,
            node_map_type: NodeMapType = NodeMapType.REMOTE_DEVICE) -> None:
        """Assign the given value to the specified node."""
        node = self._node_maps[node_map_type].FindNode(node_name)

        if isinstance(value, str):
            cast(ids_peak.StringNode, node).SetValue(value)
        elif isinstance(value, bool):
            cast(ids_peak.BooleanNode, node).SetValue(value)
        elif isinstance(value, int):
            cast(ids_peak.IntegerNode, node).SetValue(value)
        elif isinstance(value, float):
            cast(ids_peak.FloatNode, node).SetValue(value)
        else:
            raise TypeError("Unhandled node type!")

    def get_node_value(
            self, node_name: str,
            node_map_type: NodeMapType = NodeMapType.REMOTE_DEVICE
    ) -> str | bool | int | float:
        """Return the value of the specified node."""
        node = self._node_maps[node_map_type].FindNode(node_name)

        if isinstance(node, ids_peak.StringNode):
            return cast(ids_peak.StringNode, node).Value()
        elif isinstance(node, ids_peak.BooleanNode):
            return cast(ids_peak.BooleanNode, node).Value()
        elif isinstance(node, ids_peak.IntegerNode):
            return cast(ids_peak.IntegerNode, node).Value()
        elif isinstance(node, ids_peak.FloatNode):
            return cast(ids_peak.FloatNode, node).Value()
        else:
            raise TypeError("Unhandled node type!")

    def exec_command_node_and_wait(
            self, node_name: str,
            node_map_type: NodeMapType = NodeMapType.REMOTE_DEVICE) -> None:
        """Execute the specified command and wait for it to complete."""
        node = cast(ids_peak.CommandNode,
                    self._node_maps[node_map_type].FindNode(node_name))
        node.Execute()
        node.WaitUntilDone()

    def load_user_set(self, user_set: UserSet) -> None:
        """Load the specified user set."""
        self.set_enum_node_entry("UserSetSelector", user_set.selector_value)
        self.exec_command_node_and_wait("UserSetLoad")
        self._update_acquisition_mode()

    def reset_to_default(self) -> None:
        """Load user set 'Default'"""
        self.load_user_set(UserSet.DEFAULT)

    def _update_acquisition_mode(self) -> None:
        acquisition_mode_node = cast(ids_peak.EnumerationNode, self._node_maps[
            NodeMapType.REMOTE_DEVICE].FindNode(
            "AcquisitionMode"))

        acquisition_mode = acquisition_mode_node.CurrentEntry().SymbolicValue()

        if acquisition_mode == "SingleFrame":
            self._acquisition_frame_count = 1
        elif acquisition_mode == "MultiFrame":
            acquisition_frame_count_node = cast(
                ids_peak.IntegerNode,
                self._node_maps[NodeMapType.REMOTE_DEVICE].FindNode(
                    "AcquisitionFrameCount"))
            self._acquisition_frame_count = acquisition_frame_count_node.Value()
        else:
            self._acquisition_frame_count = ids_peak.DataStream.INFINITE_NUMBER

        trigger_selector_node = cast(
            ids_peak.EnumerationNode,
            self._node_maps[NodeMapType.REMOTE_DEVICE].FindNode(
                "TriggerSelector"))

        trigger_mode_node = cast(
            ids_peak.EnumerationNode,
            self._node_maps[NodeMapType.REMOTE_DEVICE].FindNode("TriggerMode"))

        trigger_source_node = cast(
            ids_peak.EnumerationNode,
            self._node_maps[NodeMapType.REMOTE_DEVICE].FindNode(
                "TriggerSource"))

        self._acquisition_mode = AcquisitionMode.FREERUN

        available_entries = trigger_selector_node.AvailableEntries()
        for entry in _frame_start_trigger_entries:
            if entry in available_entries:
                trigger_selector_node.SetCurrentEntry(entry)
                if trigger_mode_node.CurrentEntry().SymbolicValue() != "On":
                    continue

                trigger = trigger_source_node.CurrentEntry().SymbolicValue()
                self._acquisition_mode = (
                    AcquisitionMode.SOFTWARE_TRIGGER if trigger == "Software"
                    else AcquisitionMode.UNKNOWN)
                break

    def _lock_tl_params(self, lock: bool) -> None:
        self.set_node_value("TLParamsLocked", 1 if lock else 0)

    def set_acquisition_frame_count(self, count: int) -> None:
        """
        Configure the number of frames to be acquired.

        Parameters
        ----------
        count : int
            The requested number of frames to capture. Depending on this value,
            the camera operates in one of the following modes:
            - SingleFrame: count == 1
            - MultiFrame: 1 < count <= maximum supported frame count
            - Continuous: count exceeds the maximum supported frame count
        """
        frame_count_node = cast(ids_peak.IntegerNode, self._node_maps[
            NodeMapType.REMOTE_DEVICE].FindNode(
            "AcquisitionFrameCount"))

        if count == 1:
            self.set_enum_node_entry("AcquisitionMode", "SingleFrame")
        elif count > frame_count_node.Maximum():
            self.set_enum_node_entry("AcquisitionMode", "Continuous")
        else:
            self.set_enum_node_entry("AcquisitionMode", "MultiFrame")
            frame_count_node.SetValue(count)
        self._acquisition_frame_count = count

    def start_acquisition(self, buffer_count_hint: int | None) -> None:
        """
        Start acquisition.

        Parameters
        ----------
        buffer_count_hint : int, optional
            Suggested minimum number of buffers to allocate for acquisition.
            The actual allocated buffer count may be higher.
        """
        min_required = self._data_stream.NumBuffersAnnouncedMinRequired()
        if buffer_count_hint is None or buffer_count_hint < min_required:
            buffer_count = min_required
        else:
            buffer_count = buffer_count_hint

        self._alloc_buffers(buffer_count)
        self._lock_tl_params(True)
        self._data_stream.StartAcquisition(
            ids_peak.AcquisitionStartMode_Default,
            self._acquisition_frame_count)

        self.exec_command_node_and_wait("AcquisitionStart")

    def stop_acquisition(self) -> None:
        """Stop acquisition."""
        self.exec_command_node_and_wait("AcquisitionStop")

        self._data_stream.StopAcquisition()
        self._lock_tl_params(False)

    def acquire_image_buffer(self, timeout_ms: int) -> ids_peak.Buffer:
        """Acquire an image buffer from the camera.

        If the camera is configured for software trigger mode, a software
        trigger is executed before acquiring the buffer.

        Args:
            timeout_ms: Maximum time to wait for the buffer, in milliseconds.
        """
        if self._acquisition_mode == AcquisitionMode.SOFTWARE_TRIGGER:
            self.exec_command_node_and_wait("TriggerSoftware")
        return self._data_stream.WaitForFinishedBuffer(
            ids_peak.Timeout(timeout_ms))

    def queue_buffer(self, buffer: ids_peak.Buffer) -> None:
        """Re-queue a buffer that is no longer needed."""
        self._data_stream.QueueBuffer(buffer)

    def _revoke_buffers(self) -> None:
        self._data_stream.Flush(
            ids_peak.DataStreamFlushMode_AllToInputPool)

        for buffer in self._data_stream.AnnouncedBuffers():
            self._data_stream.RevokeBuffer(buffer)

    def _alloc_buffers(self, num_buffers: int = 5) -> None:
        self._revoke_buffers()

        if self._data_stream.DefinesPayloadSize():
            payload_size = self._data_stream.PayloadSize()
        else:
            payload_size = cast(int, self.get_node_value("PayloadSize"))

        for _ in range(num_buffers):
            buffer = self._data_stream.AllocAndAnnounceBuffer(payload_size)
            self._data_stream.QueueBuffer(buffer)

    def set_acquisition_mode(self, mode: AcquisitionMode) -> None:
        """Set acquisition mode."""
        assert (mode == AcquisitionMode.SOFTWARE_TRIGGER or
                mode == AcquisitionMode.FREERUN)

        trigger_selector_node = cast(
            ids_peak.EnumerationNode,
            self._node_maps[NodeMapType.REMOTE_DEVICE].FindNode(
                "TriggerSelector"))

        trigger_mode_node = cast(
            ids_peak.EnumerationNode,
            self._node_maps[NodeMapType.REMOTE_DEVICE].FindNode("TriggerMode"))

        available_entries = [x.SymbolicValue() for x in
                             trigger_selector_node.AvailableEntries()]

        # disable all frame start triggers
        for entry in _frame_start_trigger_entries:
            if entry not in available_entries:
                continue
            trigger_selector_node.SetCurrentEntry(entry)
            if (trigger_mode_node.CurrentEntry().SymbolicValue() != "Off"
                    and trigger_mode_node.IsWriteable()):
                trigger_mode_node.SetCurrentEntry("Off")

        if mode == AcquisitionMode.SOFTWARE_TRIGGER:
            # find first available frame start trigger
            trigger = next((x for x in _frame_start_trigger_entries if
                            x in available_entries), None)

            if trigger is None:
                raise RuntimeError(
                    f"Camera does not support acquisition mode: {mode}")

            trigger_selector_node.SetCurrentEntry(trigger)
            self.set_enum_node_entry("TriggerSource", "Software")
            trigger_mode_node.SetCurrentEntry("On")

        self._acquisition_mode = mode
