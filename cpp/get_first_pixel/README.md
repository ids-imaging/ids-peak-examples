# Get First Pixel Example

This example demonstrates how to acquire an image and print the value of the first pixel.

## Workflow

The example performs the following steps:

1. Searches for available devices and waits for user selection.
2. Opens the selected device.
3. Starts acquisition, acquires images and prints the value of the first pixel.
4. Stops acquisition and cleans up buffers.

## Requirements

To run this example, you need:

- An **IDS** camera
- [IDS peak standard Setup](https://en.ids-imaging.com/download-peak.html) version 2.19 or later
- **CMake** version 3.10 or later
- A supported C++ compiler (MSVC, GCC, or Clang)
