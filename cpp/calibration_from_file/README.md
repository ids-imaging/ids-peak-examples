# Calibration Example

This example demonstrates how to perform a camera calibration by using images from file.
The images contain a [calibration plate](https://en.ids-imaging.com/download-details/1012041.html)
in different poses and position, which will improve the calibration result.
In addition, the calibration Algorithm needs a corresponding
[description file](../../data/calibration_from_file/1012041-radon-checkerboard-marker-65mm-6x6.json) matching the calibration plate.
It can be obtained on the IDS [Website](https://en.ids-imaging.com/download-details/1012041.html).
When the calibration algorithm is done processing, the calibration result is saved to a file, containing both,
intrinsic and extrinsic calibration, as well as backprojection errors, indicating the quality of the calibration.

## Requirements

This example depends on the following components:

- [IDS peak standard Setup](https://en.ids-imaging.com/download-peak.html) version 2.20 or later
- **CMake** version 3.10 or later
- A supported C++ compiler (MSVC, GCC, or Clang)
