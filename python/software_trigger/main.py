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
This example shows how to capture images using a software trigger with
the IDS peak generic API.
The application opens the first available camera, enables software
trigger mode, and provides an interactive console to trigger image
acquisition manually.

Each trigger captures one frame, converts it using the IDS peak image
pipeline, and saves it as a PNG file in the specified output directory
using a timestamp as the filename.
"""

from __future__ import annotations

import os
import cmd
import sys
import time
import argparse

from ids_peak import ids_peak
from ids_peak_icv.pipeline import DefaultPipeline
from ids_peak_common import PixelFormat

from typing import Optional, Type, cast
from types import TracebackType


class SoftwareTriggerExample:
    def __init__(
        self,
        output_directory: str,
        exposure: Optional[float] = None,
        gain: Optional[float] = None,
    ) -> None:
        self.device: Optional[ids_peak.Device] = None
        self.remote_nodemap: Optional[ids_peak.NodeMap] = None
        self.data_stream: Optional[ids_peak.DataStream] = None
        self._output_directory = output_directory
        self._exposure = exposure
        self._gain = gain
        # Create an instance of the default pixel pipeline which defines a sequence of processing
        # steps that are applied to an acquired image. The image is then processed into an image
        # of the specified output pixel format.
        self._image_pipeline = DefaultPipeline()
        self._image_pipeline.output_pixel_format = PixelFormat.BGRA_8

    def __enter__(self) -> SoftwareTriggerExample:
        # Initialize library, has to be matched by a Library.Close() call
        ids_peak.Library.Initialize()
        return self

    def __exit__(
        self,
        _exc_type: Optional[Type[BaseException]],
        _exc_value: Optional[BaseException],
        _traceback: Optional[TracebackType]
    ) -> Optional[bool]:
        # Initialize library, has to be matched by a Library.Close() call
        ids_peak.Library.Close()
        return None

    def load_defaults(self) -> None:
        if self.remote_nodemap is None:
            raise RuntimeError("Device is not opened!")

        cast(ids_peak.EnumerationNode,
             self.remote_nodemap.FindNode("UserSetSelector")).SetCurrentEntry("Default")
        user_set_load_node = cast(ids_peak.CommandNode, self.remote_nodemap.FindNode("UserSetLoad"))
        user_set_load_node.Execute()
        user_set_load_node.WaitUntilDone()

    def apply_camera_configuration(self) -> None:
        if self.remote_nodemap is None:
            raise RuntimeError("Device is not opened!")

        if self._exposure is not None:
            node = cast(ids_peak.FloatNode, self.remote_nodemap.FindNode("ExposureTime"))
            # For some devices the ExposureTime node may not be writable,
            # e.g. due to the auto features being active on the camera.
            if not node.IsWriteable():
                raise RuntimeError(
                    "Failed to write requested exposure time, since "
                    "the 'ExposureTime' node is not writable!"
                )

            node.SetValue(self._exposure)
        if self._gain is not None:
            gain_selector = cast(ids_peak.EnumerationNode,
                                 self.remote_nodemap.FindNode("GainSelector"))
            available_gain_entries = [x.StringValue() for x in gain_selector.AvailableEntries()]

            preferred_entries = ["AnalogAll", "DigitalAll", "All"]
            selected_gain = next(
                (e for e in preferred_entries if e in available_gain_entries), None
            )

            if selected_gain is not None:
                gain_selector.SetCurrentEntry(selected_gain)
            else:
                raise RuntimeError("Can not set gain value: no preferred gain selector available")
            gain_node = cast(ids_peak.FloatNode, self.remote_nodemap.FindNode("Gain"))
            # For some devices the Gain node may not be writable,
            # e.g. due to the auto features being active on the camera.
            if not gain_node.IsWriteable():
                raise RuntimeError(
                    "Failed to write requested gain factor, since the 'Gain' node is not writable!"
                )

            gain_node.SetValue(self._gain)

    def alloc_buffers(self) -> None:
        if self.remote_nodemap is None or self.data_stream is None:
            raise RuntimeError("Device is not opened!")

        # Buffer size
        payload_size = cast(ids_peak.IntegerNode,
                            self.remote_nodemap.FindNode("PayloadSize")).Value()

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

    def init_software_trigger(self) -> None:
        if self.remote_nodemap is None:
            raise RuntimeError("Device is not opened!")

        trigger_selector_node = cast(ids_peak.EnumerationNode,
                                     self.remote_nodemap.FindNode("TriggerSelector"))

        # In GenICam, enumeration nodes can contain multiple possible entries
        # (enum values), but not all entries are guaranteed to be available or
        # implemented on every device or in every state. According to the
        # standard, only entries with a valid access status (i.e., not
        # 'NotAvailable' or 'NotImplemented') can be selected.
        # This ensures that only legal, supported values are used
        # when configuring the device.
        all_entries = trigger_selector_node.Entries()
        available_entries = []
        for entry in all_entries:
            if (
                entry.AccessStatus() != ids_peak.NodeAccessStatus_NotAvailable
                and entry.AccessStatus() != ids_peak.NodeAccessStatus_NotImplemented
            ):
                available_entries.append(entry.SymbolicValue())

        if "ExposureStart" in available_entries:
            trigger_selector_node.SetCurrentEntry("ExposureStart")
        elif "FrameStart" in available_entries:
            trigger_selector_node.SetCurrentEntry("FrameStart")
        elif "ReadOutStart" in available_entries:
            trigger_selector_node.SetCurrentEntry("ReadOutStart")
        else:
            raise RuntimeError(
                "Software Trigger not supported: Expected one of the "
                "'ExposureStart', 'FrameStart' or 'ReadOutStart' trigger selectors."
            )

        cast(ids_peak.EnumerationNode,
             self.remote_nodemap.FindNode("TriggerMode")).SetCurrentEntry("On")
        cast(ids_peak.EnumerationNode,
             self.remote_nodemap.FindNode("TriggerSource")).SetCurrentEntry("Software")

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

    def start_acquisition(self) -> None:
        if self.remote_nodemap is None or self.data_stream is None:
            raise RuntimeError("Device is not opened!")

        # Lock writable nodes, which could influence the payload size or
        # similar information during acquisition.
        cast(ids_peak.IntegerNode, self.remote_nodemap.FindNode("TLParamsLocked")).SetValue(1)

        # Start acquisition both locally and on device.
        self.data_stream.StartAcquisition()
        acquisition_start_node = cast(ids_peak.CommandNode,
                                      self.remote_nodemap.FindNode("AcquisitionStart"))
        acquisition_start_node.Execute()
        acquisition_start_node.WaitUntilDone()

        print("Starting acquisition...")

    def stop_acquisition(self) -> None:
        if self.remote_nodemap is None or self.data_stream is None:
            raise RuntimeError("Device is not opened!")

        cast(ids_peak.CommandNode, self.remote_nodemap.FindNode("AcquisitionStop")).Execute()

        # Stop and flush the `DataStream`.
        # `KillWait` will cancel pending `WaitForFinishedBuffer` calls.
        # NOTE: One call to `KillWait` will cancel one pending `WaitForFinishedBuffer`.
        #       For more information, refer to the documentation of `KillWait`.
        if self.data_stream.IsGrabbing():
            self.data_stream.StopAcquisition(ids_peak.AcquisitionStopMode_Kill)
        # Discard all buffers from the acquisition engine.
        # They remain in the announced buffer pool.
        self.data_stream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)

        # Unlock writable nodes again. See `Lock writable nodes`.
        cast(ids_peak.IntegerNode, self.remote_nodemap.FindNode("TLParamsLocked")).SetValue(0)

    def software_trigger(self) -> None:
        if self.remote_nodemap is None:
            raise RuntimeError("Device is not opened!")

        print("Executing software trigger...")
        trigger_software_node = cast(ids_peak.CommandNode,
                                     self.remote_nodemap.FindNode("TriggerSoftware"))
        trigger_software_node.Execute()
        trigger_software_node.WaitUntilDone()
        print("Finished.")

    def get_next_image(self) -> None:
        """
        Wait for the next image buffer from the device and save
        it to disk.
        """
        if self.remote_nodemap is None or self.data_stream is None:
            raise RuntimeError("Device is not opened!")

        try:
            os.makedirs(self._output_directory, exist_ok=True)

            # Trigger an image.
            self.software_trigger()

            # Wait for the finished/filled buffer event.
            buffer = self.data_stream.WaitForFinishedBuffer(ids_peak.Timeout(5000))
            print(f"Received FrameID: {buffer.FrameID()}")

            # Convert the acquired buffer to an image view.
            # The ImageView defines a standard way to access image properties and raw pixel
            # data, enabling interoperability with different image processing libraries or
            # backends.
            # Note: This object does not own the image memory.
            image_view = buffer.ToImageView()

            # Pass the ImageView through the image pipeline which runs all processing steps
            # in sequence. The resulting image is guaranteed to be a copy.
            converted_image = self._image_pipeline.process(image_view)

            file_name = time.strftime("%Y-%m-%dT%H-%M-%S.png")
            converted_image.save(os.path.join(self._output_directory, file_name))

            # Put the buffer back in the pool, so it can be filled again.
            self.data_stream.QueueBuffer(buffer)
        except Exception as e:
            print(f"\nException: {e}")

    def prepare(self) -> None:
        try:
            # Open the first available device.
            self.open_device()

            # Load default camera settings.
            self.load_defaults()

            # Applies the command line parameters.
            self.apply_camera_configuration()

            # Allocate buffers for the acquisition.
            self.alloc_buffers()

            # Configure the software trigger.
            self.init_software_trigger()

            # Start the acquisition so we can receive images.
            self.start_acquisition()
        except ids_peak.AbortedException:
            print("Aborted")
        except Exception as e:
            print("EXCEPTION: " + str(e))
            sys.exit(-2)

    def stop(self) -> None:
        if self.remote_nodemap is not None:
            # Stop the acquisition.
            self.stop_acquisition()

            # Revoke all buffers.
            self.revoke_buffers()

    def open_device(self) -> None:
        # Update the DeviceManager.
        # When `Update` is called, it searches for all producer libraries
        # contained in the directories found in the official GenICam GenTL
        # environment variable GENICAM_GENTL{32/64}_PATH. It then opens all
        # found ProducerLibraries, their Systems, their Interfaces, and lists
        # all available DeviceDescriptors.
        ids_peak.DeviceManager.Instance().Update()

        # Open the first openable device.
        device = None
        for dev in ids_peak.DeviceManager.Instance().Devices():
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


class InteractiveSoftwareTrigger(cmd.Cmd):
    intro = (
        "Interactive software trigger console. Press help or ? to list commands.\n"
        "Hint: Type 'trigger<Enter>' or 't<Enter>' to trigger an image."
    )

    def __init__(self, example: SoftwareTriggerExample) -> None:
        super().__init__()
        self._example = example

        self._example.prepare()

    def help_trigger(self) -> None:
        print("Trigger an image via software trigger")

    def do_trigger(self, _args: str) -> None:
        self._example.get_next_image()

    def help_t(self) -> None:
        print("Alias for 'trigger'")

    def do_t(self, args: str) -> None:
        self.do_trigger(args)

    def help_exit(self) -> None:
        print("Exit the example")

    def do_exit(self, _args: str) -> bool:
        self._example.stop()
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--exposure",
        type=float,
        help="Set the exposure time in microseconds before the acquisition starts.",
    )
    parser.add_argument(
        "--gain", type=float, help="Sets the master gain factor before the acquisition starts."
    )
    parser.add_argument(
        "out_directory",
        type=str,
        help="Output directory path. Triggered images will be saved here "
        "with timestamps as their filenames.",
    )

    args = parser.parse_args()

    with SoftwareTriggerExample(
        args.out_directory,
        exposure=args.exposure,
        gain=args.gain,
    ) as example:
        interactive = InteractiveSoftwareTrigger(example)
        interactive.cmdloop()
