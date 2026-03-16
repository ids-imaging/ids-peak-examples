# Copyright (C) 2024 - 2026, IDS Imaging Development Systems GmbH.
#
# Permission to use, copy, modify, and/or distribute this software for
# any purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
# FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
# AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
This example demonstrates how to record a video using the IDS peak IPL.

The application:
- Configures a camera for acquisition
- Creates and saves a video sequence
"""

from __future__ import annotations

import os
import sys
import time
import argparse

from ids_peak import ids_peak
from ids_peak_ipl import ids_peak_ipl
from ids_peak_icv.pipeline import DefaultPipeline
from ids_peak_common import PixelFormat

from typing import Optional


class RecordVideoExample:
    def __init__(
        self,
        out_file: str,
        framerate: Optional[float] = None,
        exposure: Optional[float] = None,
        gain: Optional[float] = None,
        force: bool = False,
    ) -> None:
        # Initialize library and create a device manager
        ids_peak.Library.Initialize()

        self.device_manager: ids_peak.DeviceManager = ids_peak.DeviceManager.Instance()
        self.device: Optional[ids_peak.Device] = None
        self.remote_nodemap: Optional[ids_peak.NodeMap] = None
        self.data_stream: Optional[ids_peak.DataStream] = None
        self._out_file = out_file
        self._framerate = framerate
        self._exposure = exposure
        self._gain = gain
        self._force = force
        # Create an instance of the default pixel pipeline which defines a sequence of processing
        # steps that are applied to an acquired image. The image is then processed into an image
        # of the specified output pixel format.
        self._image_pipeline = DefaultPipeline()
        self._image_pipeline.output_pixel_format = PixelFormat.BGRA_8

    def load_defaults(self) -> None:
        if self.remote_nodemap is None:
            raise RuntimeError("Device is not opened!")

        self.remote_nodemap.FindNode("UserSetSelector").SetCurrentEntry("Default")
        self.remote_nodemap.FindNode("UserSetLoad").Execute()
        self.remote_nodemap.FindNode("UserSetLoad").WaitUntilDone()

    def apply_camera_configuration(self) -> None:
        if self.remote_nodemap is None:
            raise RuntimeError("Device is not opened!")

        if self._framerate is not None:
            self.remote_nodemap.FindNode("AcquisitionFrameRate").SetValue(self._framerate)
        if self._exposure is not None:
            self.remote_nodemap.FindNode("ExposureTime").SetValue(self._exposure)
        if self._gain is not None:
            gain_selector = self.remote_nodemap.FindNode("GainSelector")
            available_gain_entries = [x.StringValue() for x in gain_selector.AvailableEntries()]

            preferred_entries = ["AnalogAll", "DigitalAll", "All"]
            selected_gain = next(
                (e for e in preferred_entries if e in available_gain_entries), None
            )

            if selected_gain is not None:
                gain_selector.SetCurrentEntry(selected_gain)
            else:
                raise RuntimeError("Can not set gain value: no preferred gain selector available")
            self.remote_nodemap.FindNode("Gain").SetValue(self._gain)

    def alloc_buffers(self) -> None:
        if self.remote_nodemap is None or self.data_stream is None:
            raise RuntimeError("Device is not opened!")

        # Buffer size
        payload_size = self.remote_nodemap.FindNode("PayloadSize").Value()

        # Minimum number of required buffers
        buffer_count_max = self.data_stream.NumBuffersAnnouncedMinRequired()

        # Allocate buffers and add them to the pool
        for _ in range(buffer_count_max):
            # Let the TL allocate the buffers
            buffer = self.data_stream.AllocAndAnnounceBuffer(payload_size)
            # Put the buffer in the pool
            self.data_stream.QueueBuffer(buffer)

    def revoke_buffers(self) -> None:
        if self.data_stream is None:
            raise RuntimeError("Device is not opened!")

        # Remove buffers from any associated queue
        self.data_stream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)

        for buffer in self.data_stream.AnnouncedBuffers():
            # Remove buffer from the transport layer
            self.data_stream.RevokeBuffer(buffer)

    @staticmethod
    def _confirm_question(msg: str) -> bool:
        msg = f"{msg} (y[es], n[o]): "
        while True:
            try:
                answer = input(msg).lower()
                if answer in ["yes", "y"]:
                    return True
                elif answer in ["no", "n"]:
                    break
            except KeyboardInterrupt:
                break
        return False

    def run_acquisition_loop(self) -> None:
        """
        Run the acquisition loop.
        """
        if self.remote_nodemap is None or self.data_stream is None:
            raise RuntimeError("Device is not opened!")

        # Get acquisition frame rate
        frame_rate = self.remote_nodemap.FindNode("AcquisitionFrameRate").Value()

        # Create peak IPL video writer
        video_writer = ids_peak_ipl.VideoWriter()

        if os.path.exists(self._out_file):
            if self._force or RecordVideoExample._confirm_question(
                f"Overwrite existing file ({self._out_file})?"
            ):
                os.unlink(self._out_file)
            else:
                sys.exit(-1)
        video_writer.Open(self._out_file)
        video_writer.Container().SetFramerate(frame_rate)

        # Lock writable nodes, which could influence the payload size or
        # similar information during acquisition.
        self.remote_nodemap.FindNode("TLParamsLocked").SetValue(1)

        self.data_stream.StartAcquisition()
        self.remote_nodemap.FindNode("AcquisitionStart").Execute()
        self.remote_nodemap.FindNode("AcquisitionStart").WaitUntilDone()

        print("Starting acquisition...")
        print("You can stop recording when pressing Ctrl+C!")

        time_start = time.time()
        num_frames_recorded = 0
        while True:
            try:
                # Wait for the finished/filled buffer event.
                buffer = self.data_stream.WaitForFinishedBuffer(ids_peak.Timeout.INFINITE_TIMEOUT)
                print(f"\rReceived FrameID: {buffer.FrameID()}", end="")

                # Convert the acquired buffer to an image view.
                # The ImageView defines a standard way to access image properties and raw pixel
                # data, enabling interoperability with different image processing libraries or
                # backends.
                # Note: This object does not own the image memory.
                image_view = buffer.ToImageView()

                # Pass the ImageView through the image pipeline which runs all processing steps
                # in sequence. The resulting image is guaranteed to be a copy.
                converted_image = self._image_pipeline.process(image_view)

                # Append image to video
                data = converted_image.to_numpy_array().flatten()
                video_writer.Append(
                    ids_peak_ipl.Image.CreateFromSizeAndPythonBuffer(
                        converted_image.pixel_format.value,
                        data,
                        converted_image.width,
                        converted_image.height,
                    )
                )
                num_frames_recorded += 1

                # Put the buffer back in the pool, so it can be filled again.
                self.data_stream.QueueBuffer(buffer)
            except KeyboardInterrupt:
                print("\nKeyboard interrupt.")
                break
            except Exception as e:
                print(f"\nException: {e}")
        video_duration = time.time() - time_start

        print("Stopping acquisition...")
        self.remote_nodemap.FindNode("AcquisitionStop").Execute()
        self.remote_nodemap.FindNode("AcquisitionStop").WaitUntilDone()
        self.data_stream.StopAcquisition(ids_peak.AcquisitionStopMode_Default)

        # Unlock writable nodes again. See `Lock writable nodes`.
        self.remote_nodemap.FindNode("TLParamsLocked").SetValue(0)

        # AVI framerate sets the playback speed.
        # You can calculate that with the amount of frames captured in the
        # time duration the video was recorded
        video_writer.Container().SetFramerate(num_frames_recorded / video_duration)
        # Wait until all frames are written to the file
        video_writer.WaitUntilFrameDone(10000)
        video_writer.Close()

    def run(self) -> None:
        try:
            # Update the DeviceManager.
            # When `Update` is called, it searches for all producer libraries
            # contained in the directories found in the official GenICam GenTL
            # environment variable GENICAM_GENTL{32/64}_PATH. It then opens all
            # found ProducerLibraries, their Systems, their Interfaces, and lists
            # all available DeviceDescriptors.
            self.device_manager.Update()

            # Open the first available device.
            self.open_device()

            # Load default camera settings.
            self.load_defaults()

            # Applies the command line parameters.
            self.apply_camera_configuration()

            # Allocate buffers for the acquisition.
            self.alloc_buffers()

            # Run acquisition loop until an error occurs or the user presses Ctrl+C.
            self.run_acquisition_loop()

            # Revoke all buffers.
            self.revoke_buffers()

        except ids_peak.AbortedException:
            print("Aborted")
        except Exception as e:
            print("EXCEPTION: " + str(e))
            sys.exit(-2)

        finally:
            ids_peak.Library.Close()

    def open_device(self) -> None:
        # Open the first openable device.
        device = None
        for dev in self.device_manager.Devices():
            if dev.IsOpenable(ids_peak.DeviceAccessType_Control):
                device = dev.OpenDevice(ids_peak.DeviceAccessType_Control)

        # Exit the program if no device was found.
        if not device:
            raise RuntimeError("No device found. Exiting Program.")

        self.device = device

        print("Using Device " + self.device.DisplayName())
        # Retrieve the remote device's primary node map.
        # In GenICam, a node map represents a hierarchical set of parameters (features)
        # such as exposure, gain, and firmware info. The node map provides access to controls
        # implemented on the device itself, typically following the GenICam SFNC,
        # while allowing for device-specific extensions.
        self.remote_nodemap = self.device.RemoteDevice().NodeMaps()[0]
        self.data_stream = self.device.DataStreams()[0].OpenDataStream()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--framerate", type=float, help="Set the framerate before the acquisition starts."
    )
    parser.add_argument(
        "--exposure",
        type=float,
        help="Set the exposure time in microseconds before the acquisition starts.",
    )
    parser.add_argument(
        "--gain", type=float, help="Sets the master gain factor before the acquisition starts."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrites the video output file if it already exists.",
    )
    parser.add_argument(
        "out_file", type=str, help="Output file path to save the video (Supported format: .avi)"
    )

    args = parser.parse_args()

    example = RecordVideoExample(
        args.out_file,
        framerate=args.framerate,
        exposure=args.exposure,
        gain=args.gain,
        force=args.force,
    )
    example.run()
