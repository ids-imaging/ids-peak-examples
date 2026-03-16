# Record Video Example

This example demonstrates how to record a video using the IDS peak IPL.
The application opens the first available IDS camera, optionally configures
acquisition parameters such as frame rate, exposure time, and gain, and
records incoming frames to a video file.

During acquisition, received buffers are converted to images, processed
through the IDS peak image pipeline, and appended to a video container.
Recording continues until the user stops the application with `Ctrl+C`,
after which the video file is finalized and closed. To ensure compatibility
across different camera models, the example automatically selects a
supported gain selector before applying the gain value.


## Requirements

The following IDS peak python packages are required:

* `ids-peak`
* `ids-peak-ipl`
* `ids-peak-icv`
* `ids-peak-common`

To install all required dependencies, use the provided `requirements.txt`:

```
pip install -r requirements.txt
```

In addition, a suitable GenTL producer must be installed, for example via the
[IDS peak Setup](https://en.ids-imaging.com/download-peak.html).

## Running the example

After installing all requirements the demo can be run by executing `main.py` with the Python interpreter:

```
python main.py output.avi
```

### Optional parameters

The application supports several optional configuration parameters:

```
python main.py output.avi --framerate 30 --exposure 10000 --gain 2
```

| Parameter | Description |
|-----------|-------------|
| `--framerate` | Acquisition frame rate in frames per second |
| `--exposure` | Exposure time in microseconds |
| `--gain` | Master gain factor |
| `--force` | Overwrites the output file if it already exists |

Example with overwrite enabled:

```
python main.py output.avi --framerate 60 --exposure 8000 --gain 1.5 --force
```

During execution, the application prints the received frame IDs to the console and continuously writes frames to the video file.

Press `Ctrl+C` to stop the recording and finalize the video file.
