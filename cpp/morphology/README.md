# Image Region Example

This example demonstrates how to use algorithm on regions.
For a general understanding of regions, have a look at the
[Image Region from file](../image_region_from_file) example.

A region can be dilated and eroded by using a structuring element.
The structuring element is defined as a region itself.
Note, that the structuring element must not be inside the image coordinate system. It has its own coordinate system,
which may even start negative.
In this sample a structuring element in form of a rectangle is used:
```
x: -1
y: -1
width: 3
height: 3
```

The following images are scaled for visuals.

## Input Image (created at runtime)

![Input Image](../../doc/morphology/region.png)

## Output

The region is displayed in red.

**Image with dilated region:**

![Output Image with dilated region](../../doc/morphology/region_dilated.png)

**Image with eroded region:**

![Output Image with eroded region](../../doc/morphology/region_eroded.png)

## Requirements

This example depends on the following components:

- [IDS peak standard Setup](https://en.ids-imaging.com/download-peak.html) version 2.19 or later
- **CMake** version 3.10 or later
- A supported C++ compiler (MSVC, GCC, or Clang)
