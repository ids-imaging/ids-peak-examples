# Precision Time Protocol (PTP) Example

This example shows how to configure and use Precision Time Protocol (PTP)
with connected GigE cameras.

In short, the application opens the available cameras, configures PTP so one
camera acts as the master clock and the others act as slaves, waits for
synchronization, acquires images, prints buffer timestamps, and then performs
cleanup.

## Workflow

The example performs the following steps:

1. Searches for available GigE devices and opens them.
2. Configures PTP so the first opened device is the master.
3. Waits until all devices report a synchronized PTP status.
4. Starts image acquisition.
5. Captures multiple images per device and prints each buffer acquisition timestamp.
6. Stops acquisition and releases buffers.

## Note About Acquisition Start and PPS

`AcquisitionStart` is sent to devices one after another. While later cameras are still starting,
an incoming PPS edge can already trigger cameras that are running.

As a result, the first timestamps after startup may be offset between cameras. In practice, it can
take a few frames until all cameras are running and reacting to the same PPS pulse sequence.

When evaluating synchronization quality, it is therefore recommended to ignore the first frames
after startup and use subsequent frames once all cameras are stably running.

## Requirements

To run this example, you need:

- At least two **IDS** cameras
- [IDS peak standard Setup](https://en.ids-imaging.com/download-peak.html) version 26.06.2 or later
