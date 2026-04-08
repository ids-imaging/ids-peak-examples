# Calibration Example

This example demonstrates how to perform a camera calibration by using images from file.
The images contain a [calibration plate](https://en.ids-imaging.com/store/ids-calibration-plate-500-mm.html)
in different poses and position, which will improve the calibration result.
In addition, the calibration Algorithm needs a corresponding
[description file](../../data/calibration_from_file/1012041-radon-checkerboard-marker-65mm-6x6.json) matching the calibration plate.
It can be obtained on the IDS [Website](https://en.ids-imaging.com/nion-downloads.html).
When the calibration algorithm is done processing, the calibration result is saved to a file, containing both,
intrinsic and extrinsic calibration, as well as backprojection errors, indicating the quality of the calibration.

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
