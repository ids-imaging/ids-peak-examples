# HDR Image Capture and Processing Example

This example demonstrates how to acquire multiple images with different exposure times
using an IDS camera and combine them into a single High Dynamic Range (HDR) image.
It supports both live acquisition from a connected camera and offline HDR generation
from previously saved exposure sequences.

## Requirements

This example depends on the following non-Python components:

* A GenTL producer (e.g. installed via the [IDS peak Setup](https://en.ids-imaging.com/download-peak.html)).
* A compatible IDS camera.

Required third-party Python packages

* `opencv-python`
* `matplotlib`
* `numpy>2`

Required IDS peak Python packages:

* `ids-peak-common>=1.3.0`
* `ids-peak-icv>=1.3.0`
* `ids-peak>=1.14.0`

Install Python dependencies:

```commandline
pip install -r requirements.txt
```

## Running the Example

The application can either:

* Capture a sequence of images from a connected IDS camera and generate an HDR image
* Generate an HDR image from previously saved exposure images

### Capture HDR Images from Camera

Basic example:

```commandline
python main.py --min 0.5 --max 50 -n 4
```

This will:

* Capture 4 image with different exposures
* Exposure range from 0.5 ms to 50 ms
* Space exposure values logarithmically across the range

If --min and --max are not specified, a default range is used.

#### Save Results to Disk

```commandline
python main.py --min 0.5 --max 50 -o output_folder
```

Saved files include:

* `seqX_YmsZZZ.png` → individual exposure images
    * `X` = image index
    * `Y` = full milliseconds
    * `ZZZ` = decimals of the milliseconds
* `hdr_preview_8bit.png` → 8-bit preview image
* `hdr_image.tiff` → full HDR image
* `hdr_image.hdr` → Radiance HDR format

#### Select HDR Acquisition Mode

```commandline
python main.py --min 1 --max 30 --acquisition-mode MODE_NAME
```

By default, the most suitable mode is selected automatically.
With `--acquisition-mode`, a specific mode can be enforced.

Available modes:

* `AUTO` \
  Automatically selects the best available acquisition mode.
* `PROGRESSIVE` \
  In progressive mode the exposure value is changed programmatically before each image is captured.
  This mode works for every camera that changes exposure instantly.
* `SEQUENCER` \
  Sequencer mode uses the camera's sequencer feature which is preconfigured for the given exposure times.
* `QUAD_EXPOSURE` \
  Sensor feature for IMX900-based cameras that capture a single image using
  four distinct exposure times arranged in a 2×2 pixel pattern. \
  **Note**: When using `QUAD_EXPOSURE`, set `-n 4`.
* `CLEAR_HDR` \
  Sensor feature for IMX675-based cameras that capture a single image using two gain factors
  in alternating lines starting with lower gain. \
  **Note**: If you choose `CLEAR_HDR`, you also need to set `-n 2`.

Available modes are printed at runtime based on camera support.

#### Run Without GUI

For console-only or headless environments:

```commandline
python main.py --min 1 --max 30 -o output_folder --no-gui
```

* No display window is shown
* Errors and progress are printed to the console

**Note**: If no output directory is specified in `--no-gui` mode, the results are not saved.

### Process Existing Image Sequence

Instead of capturing from a camera, process images from a directory:

```commandline
python main.py -i input_folder -o output_folder
```

This will:

* Load the exposure sequence from `input_folder` (typically a previously captured set)
* Generate the HDR image
* save results to `output_folder` (optional)
* Display the HDR result (unless `--no-gui` is set)

### Command Line Arguments

| Argument                 | Description                                 |
|:-------------------------|:--------------------------------------------|
| `--min`                  | Minimum exposure in milliseconds            |
| `--max`                  | Maximum exposure in milliseconds            |
| `-n, --num-exposures`    | Number of exposures (default: 4)            |
| `-s, --serial`           | Camera serial number                        |
| `--no-gui`               | Disable GUI elements                        |
| `-o, --out-dir`          | Output directory for images                 |
| `-i, --in-dir`           | Use images from directory instead of camera |
| `-a, --acquisition-mode` | HDR acquisition mode                        |

## Notes

* `--min` and `--max` must always be provided together.
* Exposure steps are logarithmically spaced across the specified range.
* Exposure values are provided in milliseconds.
* The camera is reset to default settings before and after acquisition.
* If no acquisition mode is specified, the preferred HDR provider is selected automatically.
