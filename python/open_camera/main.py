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
This example demonstrates how to discover and open a camera using the
IDS peak generic API.

The application:
- Initializes the IDS peak library
- Detects available GenTL devices using the DeviceManager
- Allows the user to select a device
- Opens the device with control access
- Reads basic device information from the GenICam node map
  (model name, user ID, sensor name, and maximum resolution)

The example focuses on device discovery and feature access and does
not perform image acquisition.
"""

from ids_peak import ids_peak


def main() -> None:
    print("open_camera Sample")

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

        # Exit program if no device was found.
        if device_manager.Devices().empty():
            print("No device found. Exiting Program.")
            return

        # List all available devices.
        for i, device in enumerate(device_manager.Devices()):
            print(
                    str(i)
                    + ": "
                    + device.ModelName()
                    + " ("
                    + device.ParentInterface().DisplayName()
                    + "; "
                    + device.ParentInterface().ParentSystem().DisplayName()
                    + "v."
                    + device.ParentInterface().ParentSystem().Version()
                    + ")"
                    )

        # Select a device to open.
        selected_device = None
        while True:
            try:
                selected_device = int(input("Select device to open: "))
                if selected_device in range(len(device_manager.Devices())):
                    break
                else:
                    print("Invalid ID.")
            except ValueError:
                print("Please enter a correct id.")
                continue

        # Open the selected device with control access.
        # The access types correspond to the GenTL `DEVICE_ACCESS_FLAGS`.
        device = device_manager.Devices()[selected_device].OpenDevice(
                ids_peak.DeviceAccessType_Control
                )

        # Retrieve the remote device's primary node map, which in GenICam represents
        # a hierarchical set of device parameters (features) such as exposure, gain,
        # and firmware info. The remote nodemap provides access to controls implemented
        # on the device itself, primarily following the GenICam Standard Feature
        # Naming Convention (SFNC), while also supporting custom nodes to
        # accommodate device-specific features.
        nodemap_remote_device = device.RemoteDevice().NodeMaps()[0]

        # Print model name and user ID
        print("Model Name: " + nodemap_remote_device.FindNode("DeviceModelName").Value())
        try:
            print("User ID: " + nodemap_remote_device.FindNode("DeviceUserID").Value())
        except ids_peak.Exception:
            print("User ID: (unknown)")

        # Print sensor information, not knowing if device has the node "SensorName"
        try:
            print("Sensor Name: " + nodemap_remote_device.FindNode("SensorName").Value())
        except ids_peak.Exception:
            print("Sensor Name: " + "(unknown)")

        # Print resolution
        try:
            print(
                    "Max. resolution (w x h): "
                    + str(nodemap_remote_device.FindNode("WidthMax").Value())
                    + " x "
                    + str(nodemap_remote_device.FindNode("HeightMax").Value())
                    )
        except ids_peak.Exception:
            print("Max. resolution (w x h): (unknown)")

    except Exception as e:
        print("Exception: " + str(e) + "")

    finally:
        input("Press Enter to continue...")
        # One call to `Close` is required for each call to `Initialize`.
        ids_peak.Library.Close()


if __name__ == "__main__":
    main()
