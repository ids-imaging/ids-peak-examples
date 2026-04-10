# Calibration Example

This example demonstrates how to generate a 3D point cloud from raw sensor data, consisting of a depth image, an
intensity image and camera calibration parameters.

First, the input images are undistorted using the provided calibration data to correct lens distortions. The corrected
depth image combined with the intensity information is then used to create a point cloud.
Finally, the resulting point cloud is exported and saved as a .ply file for further use or visualization.

## Input Files

Depth Map:

![Depth Map](../../data/point_cloud_from_file/depth_map.tiff)

Intensity Image:

![Intensity Image](../../data/point_cloud_from_file/intensity.png)

## Output

PLY:

![Screenshot PLY](../../doc/point_cloud_from_file/point_cloud.png)

## Requirements

The following IDS peak python packages are required:

* `ids-peak-icv`
* `ids-peak-common`

To install all required dependencies, use the provided `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Running the example

After installing all requirements the demo can be run by executing `main.py`
with the Python interpreter:

```bash
python main.py
```
