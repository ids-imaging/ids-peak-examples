# Workspace Calibration Example

This example demonstrates how to undistort a distorted image using precomputed camera calibration parameters.

The calibration data from example ![calibration_from_file](../calibration_from_file)) is used to correct lens
distortions in the input image, resulting in a geometrically accurate, undistorted output. This showcases how previously
obtained calibration results can be reused to improve image quality and measurement accuracy.

The resulting image is saved next to the executable.

## Input Image

Distorted Image

![Distorted Image](../../data/undistortion_from_file/fisheye.png)

## Undistorted Image

The following image is scaled for visuals.

![Undistorted Image](../../doc/undistortion_from_file/fisheye_undistorted.png)

## Requirements

The following IDS peak python packages are required:

* `ids-peak-icv`

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
