# Image Region Example

This example demonstrates how to handle image regions with the `IDS peak ICV` library.
Regions can be interpreted as a set of points
and can fill a rectangular area of the image, but they don't necessarily have to.
As they are a set of points, their shape can be anything from a single point, over a pixelized circle, to a rectangle.
They are used to enhance image processing performance, while keeping the original image.
Several algorithms in the `IDS peak ICV` library check for an available region in the image and use it when processing.

To illustrate, how regions affect the output of algorithms, the image with its region is processed by a threshold.

## Input Image

![Input Image](../../data/image_region_from_file/beads.png)

## Output

The region is displayed in green.
The result of the threshold is displayed in red.

**Image with full region:**

![Output Image with full region](../../doc/image_region/image_full_region.png)

**Image with reduced region:**

![Output Image with full region](../../doc/image_region/image_reduced_region.png)

One can observe, that the threshold only processed the green `region` area.
Only the bubbles inside the region are colored red.

## Requirements

This example depends on the following components:

- [IDS peak standard Setup](https://en.ids-imaging.com/download-peak.html) version 2.19 or later
- **CMake** version 3.10 or later
- A supported C++ compiler (MSVC, GCC, or Clang)
