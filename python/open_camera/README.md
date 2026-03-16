# Open Camera Example

This example demonstrates how to discover and open a camera device using the
IDS peak API for Python.

The program performs the following steps:
1. Initializes the IDS peak library.
2. Uses the DeviceManager to detect all available GenTL-compatible devices.
3. Lists all discovered devices with basic interface and system information.
4. Prompts the user to select a device if multiple devices are available.
5. Opens the selected device with control access.
6. Retrieves the remote device's GenICam node map.
7. Reads and prints basic device information such as:
   - Model name
   - User-defined device ID (if available)
   - Sensor name (if available)
   - Maximum supported image resolution

The GenICam node map represents the hierarchical feature set of the device,
providing access to parameters like exposure, gain, and device metadata.
Most standard parameters follow the GenICam Standard Feature Naming Convention (SFNC),
while some devices may also expose vendor-specific features.

This example focuses on device discovery and information retrieval only.
No image acquisition is performed.


## Requirements

The following IDS peak Python packages are required:
- `ids-peak`

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
