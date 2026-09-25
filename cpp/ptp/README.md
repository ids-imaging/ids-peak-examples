# Precision Time Protocol (PTP) Example

This example shows how to configure and use Precision Time Protocol (PTP)
with connected GigE cameras.

In short, the application opens the available cameras, configures the first
camera as the only opened camera eligible to become master and the others as
slave-only, waits for synchronization, acquires images, prints buffer
timestamps, and then performs cleanup.

The first camera is expected to become master unless an external grandmaster
is present and wins the Best Master Clock Algorithm (BMCA) election. If that
happens, the first camera will synchronize as a slave, as will the other
cameras.

## Workflow

The example performs the following steps:

1. Searches for available GigE devices and opens them.
2. Configures the first opened device as the only camera eligible to become
   master; the remaining cameras are slave-only.
3. Waits up to 60 seconds for the first camera to report `Master` or `Slave`
   and for the other cameras to report `Slave`.
4. Configures a PPS-triggered exposure and starts image acquisition.
5. Captures multiple images per device and prints the buffer and exposure-start
   timestamps.
6. Stops acquisition and releases buffers.

If no opened camera reports `Master`, the example reports that the grandmaster
is outside the opened camera list.

## Note About Acquisition Start and PPS

`AcquisitionStart` is sent to devices one after another. While later cameras are still starting,
an incoming PPS edge can already trigger cameras that are running.

As a result, the first timestamps after startup may be offset between cameras. In practice, it can
take a few frames until all cameras are running and reacting to the same PPS pulse sequence.

When evaluating synchronization quality, it is therefore recommended to ignore the first frames
after startup and use subsequent frames once all cameras are stably running.

## PPS Trigger Configuration

The example uses the camera's PPS signal as the source for `ExposureStart`. The
`SignalMultiplierValue` setting controls how many images are triggered per second;
the example sets it to `1`, for one image per second. Very high values may cause
the final trigger before the next second to be skipped. The exposure time must
also be shorter than the interval between triggers, or the camera may not be able
to sustain the requested trigger rate.

The trigger can also be adjusted with settings such as `TriggerDelay` and
`TriggerDivider`. For example, with PPS, setting `SignalMultiplierValue` to `5`
and `TriggerDivider` to `2` uses every second source signal, for a nominal rate
of 2.5 frames per second. The actual rate may be lower depending
on the camera settings.

## Understanding the Timestamps

For each image, the example prints two timestamps:

- `ReadOutStart` is the buffer timestamp. It marks when image data starts being
  read out from the sensor.
- `ExposureStart` is the timestamp read from the `ChunkTimestamp` data. It marks
  when the sensor exposure starts.

PTP synchronizes the cameras' timestamp counters, but these timestamps refer to
different camera events. In particular, the time from `ExposureStart` to
`ReadOutStart` depends on the exposure time and can also vary with image size,
camera processing, and sensor type. As a result, synchronized clocks do not
necessarily produce identical `ReadOutStart` timestamps across cameras.

## Requirements

To run this example, you need:

- At least two **IDS** cameras
- [IDS peak standard Setup](https://en.ids-imaging.com/download-peak.html) version 26.06.2 or later
