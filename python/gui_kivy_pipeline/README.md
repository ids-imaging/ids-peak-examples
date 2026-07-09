# Graphical Kivy Demo Using the IDS peak DefaultPipeline


![Image of kivy pipeline demo](../../doc/gui_kivy_pipeline/image.png)

Demonstrates the new `ids-peak-icv` pixel processing pipeline together with the auto-feature module provided by `ids-peak-afl`.

This example shows how to acquire images from a camera, process them using the `DefaultPipeline`, and apply a configurable chain of image-processing modules such as pixel format conversion, binning and decimation, gain and color correction, and sharpening. It also illustrates how pipeline settings can be changed at runtime, reset to defaults, and imported or exported using JSON configuration files.

In addition, the example demonstrates how to integrate the `IDS peak AFL` auto-feature module with the pipeline to enable automatic camera controls, including auto brightness (with selectable exposure and gain policies), auto white balance, and auto focus, and how these automatic features interact with manual camera and pipeline parameters during live acquisition.

All device-specific behavior, such as setting exposure, framerate, and
supported pixel formats, is encapsulated in `camera.py`.

The `DefaultPipelineExample` class in `main.py` focuses on building the user interface
and interacting directly with the default pipeline.
`DefaultPipeline` provides convenient properties for adjusting pipeline
settings such as output pixel format, host gain, binning, and more.

Custom widgets used by this demo are defined in `custom_widgets.py`.

## Requirements

This demo depends on the following third-party packages:
* `kivy >= 2.3`
* `kivymd2 >=2.0` (or `kivymd >= 2.0` once released)
* `plyer`

The following IDS peak python packages are required:
* `ids-peak-common >= 2.0.0`
* `ids-peak-ipl >= 1.17.1`
* `ids-peak-icv >= 1.4.0`
* `ids-peak >= 1.13.0`
* `ids-peak-afl >= 2.0.0`

To install all required dependencies, use the provided `requirements.txt`:
```
pip install -r requirements.txt
```

In addition, a suitable GenTL must be installed, for example via the [IDS peak Setup](https://en.ids-imaging.com/download-peak.html).

> [!IMPORTANT]
> Kivy is currently not compatible with Python >=3.14.
> The Kivy example (our Python UI package) does not work on Python 3.14 or newer.
> This also affects distributions such as Ubuntu 26.04, which ship with Python 3.14 by default.
>
> Unfortunately, this is an upstream compatibility issue that cannot be resolved within this project.
> We will support Python 3.14 as soon as a new Kivy release adds compatibility. At the time of writing,
> the latest Kivy release dates back to 2024.
>
> See https://github.com/kivy/kivy/issues/9280 for more information.
>
> Workaround: Use Python 3.13 or earlier to run this example until an updated Kivy release becomes available.

## Running the example

After installing all requirements the demo can be run by executing `main.py` with the Python interpreter

```
python main.py
```

or, if Python files (*.py) are associated with the Python interpreter, by double-clicking the file.

## Notes

### General notes

* Kivy and OpenGL use a coordinate system that is inverted relative to
  the camera image.
  To account for this, the example enables vertical image flipping using
  the ReverseY node.
* The flip state is normally restored when the application exits.
  However, if the program terminates unexpectedly, the state may not
  reset correctly.

  If this occurs, reload the default user settings in the camera software
  to restore normal behavior.
* Due to this coordinate inversion, clockwise rotations performed in
  this example will appear as counter-clockwise rotations when the same
  pipeline settings are loaded in other applications.

### Notes on linux

The plyer file chooser used in this example requires one of the following command line tools to be installed:
* zenity (GTK)
* yad (a zenity fork)
* kdialog (KDE)

If none of these utilities are available, a dialog will notify the user,
and loading or saving pipeline settings will not be possible.

> Note for Python 3.12 or later: If you’re using plyer 2.1.0 or earlier, you must install `setuptools`.
