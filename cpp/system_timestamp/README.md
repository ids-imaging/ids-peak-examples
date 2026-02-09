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

To run this example, you need:

- An **IDS** camera
- [IDS peak standard Setup](https://en.ids-imaging.com/download-peak.html) version 2.21 or later
- **CMake** version 3.10 or later
- A supported C++ compiler (MSVC, GCC, or Clang)  
