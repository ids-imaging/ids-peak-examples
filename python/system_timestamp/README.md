# System Timestamp Example

This example demonstrates how to acquire images from an **IDS** camera and retrieve the **system timestamp** associated
with each image. It also shows how to calculate system timestamps for remote device events (e.g., `ExposureStart`)
based on device timestamps.

## Workflow

The example performs the following steps:

1. Selects the first connected device that supports **system timestamp** functionality.
2. Attempts to load the default user set to configure the device.
3. Enables `ExposureStart` events on the device if supported.
4. Acquires images from the camera and prints the **system timestamp** for each buffer.
5. Receives remote device events, maps their device timestamps to system time, and prints the corresponding system timestamps.


## Requirements
* `ids-peak-common >= 1.3.0`
* `ids-peak >= 1.15.0`

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
