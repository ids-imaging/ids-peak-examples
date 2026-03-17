# Copyright (C) 2024 - 2026, IDS Imaging Development Systems GmbH.
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
This example demonstrates how to use the unicast discovery
features of the transport layer (TL) to locate cameras that
are not in the same subnet as the host system.
"""

from ids_peak import ids_peak

from typing import Sequence
import ipaddress

producers = []
systems = []


def configure_interface(
    interface: ids_peak.Interface, allow_broadcast: bool, ip_addresses: list[ipaddress.IPv4Address]
) -> None:
    """
    Configure the discovery settings of the given interface.

    Configures the interface, adding explicit device IP addresses for unicast discovery
    and setting whether to allow broadcast discovery.

    Args:
        interface: Interface to configure.
        allow_broadcast: Whether broadcast discovery is allowed.
        ip_addresses: IPs to send a unicast discovery to.
    """
    interface_node_map = interface.NodeMaps()[0]

    node_ip_to_add = interface_node_map.TryFindNode("GevDiscoveryUnicastIPAddressToAdd")
    node_ip_add_cmd = interface_node_map.TryFindNode("GevDiscoveryUnicastIPAddressAdd")
    node_ack_broadcast = interface_node_map.TryFindNode("GevAllowDiscoveryACKBroadcast")
    node_cmd_broadcast = interface_node_map.TryFindNode("GevAllowDiscoveryCMDBroadcast")

    # Configure Unicast addresses, if supported by the transport layer (TL)
    if node_ip_to_add and node_ip_add_cmd:
        for ip in ip_addresses:
            node_ip_to_add.SetValue(int(ip))
            node_ip_add_cmd.Execute()
    else:
        print(
            f'WARNING: Interface "{interface.DisplayName()} -> '
            f'{interface.ParentSystem().CTIFullPath()}" does not support unicast discovery.'
        )

    # Configure whether broadcast is allowed, if supported by the TL
    if node_cmd_broadcast and node_ack_broadcast:
        node_cmd_broadcast.SetValue(allow_broadcast)
        node_ack_broadcast.SetValue(allow_broadcast)
    else:
        print(
            f'WARNING: Interface "{interface.DisplayName()} -> '
            f'{interface.ParentSystem().CTIFullPath()}" does not support disabling the broadcast.'
        )


def filter_interfaces(
    interface_descriptors: Sequence[ids_peak.InterfaceDescriptor],
) -> list[ids_peak.Interface]:
    """
    Filter out all interfaces other than GigEVision.

    Args:
        interface_descriptors: Descriptors of interfaces to filter.

    Returns:
        GigEVision interfaces.
    """
    filtered = []

    for descriptor in interface_descriptors:
        interface = descriptor.OpenInterface()
        node_map = interface.NodeMaps()[0]
        interface_type = node_map.FindNode("InterfaceType").CurrentEntry().StringValue()

        if interface_type != "GigEVision":
            continue

        filtered.append(interface)

    return filtered


def get_interfaces() -> list[ids_peak.Interface]:
    """
    Gather all GigEVision interfaces from available transport layers.

    Returns:
        List of all GigEVision interfaces.
    """

    interfaces: list[ids_peak.Interface] = []

    # Get Paths of the installed transport layers
    cti_paths = ids_peak.EnvironmentInspector.CollectCTIPaths()

    for path in cti_paths:
        try:
            producer = ids_peak.ProducerLibrary.Open(path)
            system = producer.System().OpenSystem()

            # Hold onto producers and systems, otherwise they will be closed
            producers.append(producer)
            systems.append(system)
        except ids_peak.Exception as e:
            print(f"Failed to load and open cti: {path} with error: {e}")
            continue

        system.UpdateInterfaces(ids_peak.Timeout(500))
        descriptors = system.Interfaces()
        filtered = filter_interfaces(descriptors)

        interfaces.extend(filtered)

    return interfaces


def get_ip_addresses() -> list[ipaddress.IPv4Address]:
    """
    Prompt the user to enter IP addresses to be discovered.

    Returns:
        List of valid unicast IP addresses.
    """
    unicast_ips: list[ipaddress.IPv4Address] = []

    print(
        "Please enter the IP addresses of the devices you want to find. Press Enter without "
        "input to continue."
    )

    while True:
        try:
            ip_str = input("Enter IP Address: ").strip()
        except EOFError:
            break

        if not ip_str:
            break

        try:
            unicast_ips.append(ipaddress.IPv4Address(ip_str))
        except ValueError:
            print("Invalid input.")
            continue

    return unicast_ips


def select_interface(interfaces: list[ids_peak.Interface]) -> ids_peak.Interface:
    """
    Prompt the user to select an interface from a list.

    Args:
        interfaces: List of interfaces to choose from.

    Returns:
        Selected interface object.
    """

    while True:
        for i, iface in enumerate(interfaces):
            print(f'{i} | {iface.DisplayName()} -> "{iface.ParentSystem().CTIFullPath()}"')

        try:
            selected = int(input("\nSelect Interface: "))
            if 0 <= selected < len(interfaces):
                return interfaces[selected]
            else:
                print("Invalid input.")
        except ValueError:
            print("Invalid input.")


def print_devices(devices: Sequence[ids_peak.DeviceDescriptor]) -> None:
    """
    Print device information for each device.

    Args:
        devices: Devices to be listed.
    """
    for descriptor in devices:
        openable = "Openable" if descriptor.IsOpenable() else "No Access"
        print(
            f"{descriptor.DisplayName()}({openable}) | "
            f"{descriptor.ParentInterface().DisplayName()} -> "
            f'"{descriptor.ParentInterface().ParentSystem().CTIFullPath()}"'
        )


def find_devices_via_unicast(
    interface: ids_peak.Interface, ip_addresses: list[ipaddress.IPv4Address]
) -> list[ids_peak.DeviceDescriptor]:
    """
    Search for devices via unicast and without broadcast.

    Args:
        interface: Interface to send unicast discovery on.
        ip_addresses: IP addresses of the devices to discover.

    Returns:
        Found device descriptors.
    """
    # Configure interfaces to discover via unicast and unicast only
    configure_interface(interface, allow_broadcast=False, ip_addresses=ip_addresses)

    # Send device discoveries and listen for replies
    interface.UpdateDevices(1000)

    devices = interface.Devices()
    return list(devices)


def main() -> None:
    # The library must be initialized before use.
    # Each `Initialize` call must be matched with a corresponding call
    # to `Close`.
    ids_peak.Library.Initialize()

    try:
        interfaces = get_interfaces()
        if not interfaces:
            print("No interfaces found.")
            return

        interface = select_interface(interfaces)
        print(f"Selected Interface: {interface.DisplayName()}")

        ip_addresses = get_ip_addresses()

        # NOTE: Devices will only be discovered via unicast, so that no broadcasts are sent.
        #       Therefore, only devices with IP addresses entered above will be found.
        #       Also, this will only list GigEVision devices, USB devices will not be searched for.
        device_descriptors = find_devices_via_unicast(interface, ip_addresses)

        if not device_descriptors:
            print("Did not find any devices.")
        else:
            print("Found Devices:")
            print_devices(device_descriptors)
    finally:
        # Each `Initialize` call must be matched with a corresponding call to `Close`.
        ids_peak.Library.Close()


if __name__ == "__main__":
    main()
