# Threshold Example

This example demonstrates how to apply a threshold to an image. The output of the threshold operation is a region, which
is a set of points. The region object may be set to the image, which will then influence further image processing
algorithms in terms of behavior and computing time. The less points a region contains, the faster will following
algorithms be (when they support region processing).

In order to visualize the region, the region is painted into the image. The resulting image is saved next to the
executable.

## Input Image

![Input Image](../../data/threshold_from_file/beads.png)

## Thresholded Image

Thresholded data in red:

![Input Image](../../doc/threshold_from_file/beads_thresholded.png)

## Requirements

This example depends on the following components:

- [IDS peak standard Setup](https://en.ids-imaging.com/download-peak.html) version 2.19 or later
- **CMake** version 3.10 or later
- A supported C++ compiler (MSVC, GCC, or Clang)
