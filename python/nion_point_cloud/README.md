# Depth Map Acquisition and Point Cloud Generation Example

Demonstrates how to acquire multipart image data from an **IDS Nion** camera
and convert it into a metric 3D point cloud with per-point intensity information (XYZI).

This example shows how to open and configure an IDS Nion camera,
acquire multipart image buffers containing a depth map and an intensity image,
and process this data into usable 3D information.
It illustrates how to convert raw depth values into floating-point metric coordinates,
filter invalid or out-of-range depth measurements,
and apply factory calibration data to undistort both depth and intensity images.

In addition, the example demonstrates how to generate a point cloud from the processed depth data,
associate each 3D point with an intensity value,
and write the resulting depth maps, intensity images, and point cloud data to disk
for further processing or visualization.

## Example workflow

The example performs the following steps:

- Opens the first connected `IDS Nion` camera
- Configures camera parameters such as exposure time and confidence threshold
- Acquires multipart image data (depth map and intensity image)
- Converts the raw depth map into metric floating-point coordinates
- Filters invalid and out-of-range depth values
- Undistorts depth and intensity images using factory calibration data
- Generates a 3D point cloud with per-point intensity values (XYZI)
- Writes depth maps, intensity images, and point cloud files to disk

## Requirements

This example depends on the following components:

- An `IDS Nion` camera
- [IDS peak standard Setup](https://en.ids-imaging.com/download-peak.html) version 2.19 or later
- `ids-peak-common >= 1.1.0`
- `ids-peak-icv >= 1.0.0`
- `ids-peak >= 1.13.0`

To install all required python dependencies, use the provided `requirements.txt`:

```
pip install -r requirements.txt
```

In addition, a suitable GenTL must be installed, for example via
the [IDS peak Setup](https://en.ids-imaging.com/download-peak.html).

## Running the example

After installing all requirements the example can be run by executing `main.py` with the Python interpreter

```
python main.py
```

or, if Python files (*.py) are associated with the Python interpreter, by double-clicking the file.

## Notes

### General notes

- This example assumes that the camera settings for binning and ROI remain unchanged for each image. However, if these
  conditions change, it is advisable to refer to the chunk data.
- This example is limited to the minimum requirements for operating an IDS Nion. In principle, a workspace
  calibration can also be performed. We will describe the associated procedure in an additional example.
