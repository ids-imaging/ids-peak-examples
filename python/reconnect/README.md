# Reconnect Example

This example demonstrates how to use the automatic device reconnect
feature of the IDS peak API and how to react to connection state changes.

The application registers callbacks in the DeviceManager to receive
notifications when the connection state of a device changes. This allows
applications to react to temporary connection interruptions without
manually reopening the device.

The following device events are supported:

Disconnected:
    Device communication has been lost, but the transport layer is still
    able to attempt an automatic reconnect when the device becomes
    available again.

Reconnected:
    A previously disconnected device has been successfully reconnected
    automatically by the transport layer.

Lost:
    The device has been permanently lost and cannot be recovered by the
    transport layer. This can occur if reconnect is disabled or if the
    device was closed or not opened to begin with.

Found:
    A new device has been discovered during a device discovery update.
    A device that was previously lost and later reappears is also
    reported as a newly found device.

The example performs the following steps:

1. Initializes the IDS peak library
2. Registers callbacks for device discovery and connection events
3. Opens the first available device
4. Enables the reconnect functionality in the transport layer
5. Allocates acquisition buffers and starts image acquisition
6. Processes incoming image buffers while monitoring connection events

If a reconnect occurs, the example verifies whether the device state
and buffer configuration are still valid. If necessary, it reallocates
buffers and restarts acquisition.

This example demonstrates how to build robust camera applications that
can tolerate temporary connection interruptions such as cable unplugging,
network issues, or device reboots.


## Requirements
It is designed to work with these `IDS peak` python packages:
* `ids-peak`

To install all required dependencies, use the provided `requirements.txt`:
```
pip install -r requirements.txt
```

In addition, a suitable GenTL must be installed, for example via the [IDS peak Setup](https://en.ids-imaging.com/download-peak.html).

## Running the example

After installing all requirements the demo can be run by executing `main.py` with the Python interpreter

```
python main.py
```

or, if Python files (*.py) are associated with the Python interpreter, by double-clicking the file.
