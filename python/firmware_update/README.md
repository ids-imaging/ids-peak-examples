# Firmware Update Example

This example demonstrates how to programmatically update the firmware of
connected devices using the IDS peak generic API for Python.

The application:
1. Initializes the IDS peak library
2. Detects available GenTL devices using the DeviceManager
3. Identifies devices compatible with the provided firmware file (GUF)
4. Prompts the user for confirmation before updating
5. Executes the firmware update process
6. Reports update progress via callback functions

Progress callbacks provide information about update start, progress,
individual update steps, successful completion, or failure.

The firmware file must be provided as a command line argument in the
Generic Update Format (GUF).

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
python main.py <firmware_file.guf>
```
