# Image Region Example

This example demonstrates how to use algorithm on regions.
For a general understanding of regions, have a look at the
[Image Region from file](../image_region_from_file) example.

A region can be dilated and eroded by using a structuring element.
The structuring element is defined as a region itself.
Note, that the structuring element must not be inside the image coordinate system. It has its own coordinate system,
which may even start negative.
In this example a structuring element in form of a rectangle is used:
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
