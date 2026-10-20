# Sequencer Example

This console example configures an IDS camera sequencer, captures four images,
and saves them in the current working directory. Exposure time and gain vary
between the four sequencer sets.

For more information about the trigger techniques used in this example, have a look at this
[tech tip](https://en.ids-imaging.com/techtipp-details/items/techtip-gev-trigger-ctl.html).

## Workflow

1. Opens the first available camera and loads its default user set.
2. Checks if all necessary nodes for sequencing are available.
3. Captures one image per set and saves `sequencer_image_1.png` through
   `sequencer_image_4.png`.
4. Stops acquisition and releases the image buffers.

After acquisition starts, one `CounterReset` command starts a Counter0 burst.
Counter0 triggers the four exposures, and sequencer sets advance on
`ExposureStart` with `RisingEdge`.

## Requirements

- An IDS camera with Sequencer and Counter support
- [IDS peak Setup](https://en.ids-imaging.com/download-peak.html) version 26.06.2 or later
- CMake version 3.10 or later
- A supported C++ compiler (MSVC, GCC, or Clang)
