"""
Copyright(C) 2026, IDS Imaging Development Systems GmbH.

Permission to use, copy, modify, and/or distribute this software for
any purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

from ids_peak import ids_peak
import datetime
from typing import Optional, cast


IMAGE_COUNT_MAX = 10


def is_system_timestamp_supported(device: ids_peak.Device) -> bool:
    """
    Returns True if the device implements all nodes required for system timestamp support.

    Args:
        device: IDS peak device to check.

    Returns:
        True if system timestamp is supported, False otherwise.
    """
    node_map = device.NodeMaps()[0]

    try:
        return (
            node_map.FindNode("SynchronizationTimestampMode").IsImplemented()
            and node_map.FindNode("SynchronizationTimestampSystem").IsImplemented()
            and node_map.FindNode("SynchronizationTimestampDevice").IsImplemented()
            and node_map.FindNode("SynchronizationTimestampInterval").IsImplemented()
            and node_map.FindNode("SynchronizationTimestampLatch").IsImplemented()
        )
    except Exception:
        # Any missing node means system timestamp is not supported
        return False


def get_first_device_with_system_timestamp_support() -> Optional[ids_peak.Device]:
    """
    Select the first connected device that implements system timestamp nodes.

    Returns:
        The opened device if a compatible device is found, otherwise None.
    """
    device_manager = ids_peak.DeviceManager.Instance()
    device_manager.Update()

    if not device_manager.Devices():
        print("No camera found. Exiting program.")
        return None

    # Iterate through all connected devices
    for device_descriptor in device_manager.Devices():
        try:
            device = device_descriptor.OpenDevice(ids_peak.DeviceAccessType_Control)
            if is_system_timestamp_supported(device):
                return device
        except Exception:
            # Could not open device or not compatible, try next
            continue

    # No compatible device found
    print("No device supports system timestamps.")
    return None


def disable_device_trigger(node_map_remote_device: ids_peak.NodeMap) -> None:
    required_nodes = ["TriggerSelector", "TriggerMode"]

    for node in required_nodes:
        if not node_map_remote_device.HasNode(node):
            return

    node_trigger_selector = cast(ids_peak.EnumerationNode,
                                 node_map_remote_device.FindNode("TriggerSelector"))
    node_trigger_mode = cast(ids_peak.EnumerationNode,
                             node_map_remote_device.FindNode("TriggerMode"))

    trigger_selector_disable_preference = ["ExposureStart", "FrameStart"]

    for selector_value in trigger_selector_disable_preference:
        if node_trigger_selector.HasEntry(selector_value):
            node_trigger_selector.SetCurrentEntry(selector_value)
            node_trigger_mode.SetCurrentEntry("Off")
            break


def configure(device: ids_peak.Device) -> None:
    """
    Configure the device for freerun acquisition.

    Triggers are disabled if loading the default UserSet fails.

    Args:
        device: The opened IDS peak device.
    """
    # Get the remote device node map
    node_map_remote = device.RemoteDevice().NodeMaps()[0]

    # General preparations for untriggered continuous image acquisition
    try:
        # Load the default user set to reset device parameters
        cast(ids_peak.EnumerationNode, node_map_remote.FindNode("UserSetSelector")).SetCurrentEntry(
            "Default"
        )
        node_userset_load = cast(ids_peak.CommandNode, node_map_remote.FindNode("UserSetLoad"))
        node_userset_load.Execute()
        node_userset_load.WaitUntilDone()
    except Exception:
        # UserSet is not available, try manual freerun configuration
        print("Failed to load UserSet Default. Manual freerun configuration.")
        disable_device_trigger(node_map_remote)


def prepare_and_start_acquisition(
    device: ids_peak.Device,
) -> ids_peak.DataStream:
    """
    Prepare and start data stream acquisition.

    Allocates and announces the minimum required buffers and locks
    critical parameters.

    Args:
        device: The opened IDS peak device.

    Returns:
        The opened and started DataStream object.
    """
    data_stream = device.DataStreams()[0].OpenDataStream()
    node_map_remote_device = device.RemoteDevice().NodeMaps()[0]

    # Allocate and announce image buffers
    payload_size = cast(
        ids_peak.IntegerNode, node_map_remote_device.FindNode("PayloadSize")
    ).Value()
    num_buffers_min = data_stream.NumBuffersAnnouncedMinRequired()

    for _ in range(num_buffers_min):
        buffer = data_stream.AllocAndAnnounceBuffer(payload_size)
        data_stream.QueueBuffer(buffer)

    # Lock critical features during acquisition
    cast(ids_peak.IntegerNode, node_map_remote_device.FindNode("TLParamsLocked")).SetValue(1)

    # Start acquisition
    data_stream.StartAcquisition()
    cast(ids_peak.CommandNode, node_map_remote_device.FindNode("AcquisitionStart")).Execute()

    return data_stream


def enable_remote_device_events_if_possible(
    device: ids_peak.Device,
) -> Optional[ids_peak.EventController]:
    """
    Enable remote device events (e.g., ExposureStart) if supported.

    Used to demonstrate mapping device event timestamps to system timestamps.

    Args:
        device: The opened IDS peak device.

    Returns:
        EventController if events are supported, otherwise None.
    """
    try:
        node_map_remote = device.RemoteDevice().NodeMaps()[0]
        cast(ids_peak.EnumerationNode, node_map_remote.FindNode("EventSelector")).SetCurrentEntry(
            "ExposureStart"
        )
        cast(
            ids_peak.EnumerationNode, node_map_remote.FindNode("EventNotification")
        ).SetCurrentEntry("On")

        return cast(ids_peak.EventController, device.EnableEvents(ids_peak.EventType_RemoteDevice))
    except Exception:
        return None


def calculate_and_print_system_timestamp(
    device: ids_peak.Device,
    event_controller: ids_peak.EventController,
) -> None:
    """
    Calculate and print the system timestamp of a remote device event.

    Maps the device event timestamp to system time using the last
    synchronized device-system timestamp pair. A latch is used to
    ensure a consistent snapshot.

    Args:
        device: The opened IDS peak device.
        event_controller: Active remote device event controller.
    """
    node_map_remote = device.RemoteDevice().NodeMaps()[0]

    # Wait for event
    event = event_controller.WaitForEvent(ids_peak.Timeout(5000))
    node_map_remote.UpdateEventNodes(event)

    # Device-specific timestamp (NOT system timestamp)
    event_timestamp_ns = cast(
        ids_peak.IntegerNode, node_map_remote.FindNode("EventExposureStartTimestamp")
    ).Value()

    node_map_device = device.NodeMaps()[0]

    # Execute latch to avoid race conditions
    latch_node = cast(
        ids_peak.CommandNode, node_map_device.FindNode("SynchronizationTimestampLatch")
    )
    latch_node.Execute()
    latch_node.WaitUntilDone()

    system_timestamp_ns = cast(
        ids_peak.IntegerNode, node_map_device.FindNode("SynchronizationTimestampSystem")
    ).Value()

    device_timestamp_ns = cast(
        ids_peak.IntegerNode, node_map_device.FindNode("SynchronizationTimestampDevice")
    ).Value()

    event_system_timestamp_ns = system_timestamp_ns + (event_timestamp_ns - device_timestamp_ns)

    print("--ExposureStartEvent--")
    print(f"Timestamp [ns]: {event_timestamp_ns}")
    print(f"System timestamp [ns since epoch]: {event_system_timestamp_ns}")

    print_structured_timestamp(event_system_timestamp_ns, use_utc=False)
    print_structured_timestamp(event_system_timestamp_ns, use_utc=True)


def stop_acquisition(data_stream: ids_peak.DataStream) -> None:
    """
    Stop acquisition and release all buffers.

    Unlocks previously locked parameters.

    Args:
        data_stream: Active data stream.
    """
    node_map_remote = data_stream.ParentDevice().RemoteDevice().NodeMaps()[0]

    data_stream.StopAcquisition()
    cast(ids_peak.CommandNode, node_map_remote.FindNode("AcquisitionStop")).Execute()

    # Unlock parameters
    cast(ids_peak.IntegerNode, node_map_remote.FindNode("TLParamsLocked")).SetValue(0)

    # Flush and revoke all buffers
    data_stream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)

    for buffer in data_stream.AnnouncedBuffers():
        data_stream.RevokeBuffer(buffer)


def print_structured_timestamp(timestamp_ns: int, use_utc: bool) -> None:
    """
    Print a structured timestamp in human-readable form.

    Accepts timestamps in nanoseconds since Unix epoch.

    Args:
        timestamp_ns: Timestamp in nanoseconds since Unix epoch.
        use_utc: If True prints UTC time, otherwise local time.
    """
    seconds = timestamp_ns // 1_000_000_000
    nanoseconds_after_seconds = timestamp_ns % 1_000_000_000

    milliseconds = nanoseconds_after_seconds // 1_000_000
    microseconds = (nanoseconds_after_seconds // 1_000) % 1_000
    nanoseconds = nanoseconds_after_seconds % 1_000

    if use_utc:
        dt = datetime.datetime.utcfromtimestamp(seconds)
        label = "[UTC]"
    else:
        dt = datetime.datetime.fromtimestamp(seconds)
        label = "[Local]"

    print(
        f"Structured timestamp: {label} "
        f"{dt.strftime('%Y-%m-%d %H:%M:%S')}:"
        f"{milliseconds}:{microseconds}:{nanoseconds}"
    )


def main() -> None:
    """
    Main program entry point.

    Initializes the IDS peak library, performs acquisition,
    prints system timestamps, and cleans up resources.
    """
    try:
        ids_peak.Library.Initialize()

        device = get_first_device_with_system_timestamp_support()
        if device is None:
            raise RuntimeError("No compatible device found!")

        configure(device)
        data_stream = prepare_and_start_acquisition(device)

        event_controller = enable_remote_device_events_if_possible(device)

        image_count = 0

        while image_count < IMAGE_COUNT_MAX:
            # Wait for a finished buffer
            buffer = data_stream.WaitForFinishedBuffer(ids_peak.Timeout(5000))

            # Retrieve buffer system timestamp (ns since Unix epoch)
            system_timestamp_ns = buffer.SystemTimestamp_ns()

            print("--Buffer--")
            print(f"System timestamp [ns since epoch]: {system_timestamp_ns}")

            print_structured_timestamp(system_timestamp_ns, use_utc=False)
            print_structured_timestamp(system_timestamp_ns, use_utc=True)

            if event_controller:
                calculate_and_print_system_timestamp(device, event_controller)

            # Return buffer to acquisition queue
            data_stream.QueueBuffer(buffer)
            image_count += 1

        stop_acquisition(data_stream)
        ids_peak.Library.Close()

    except Exception as exc:
        print("EXCEPTION:", exc)
        try:
            ids_peak.Library.Close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
