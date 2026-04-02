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
