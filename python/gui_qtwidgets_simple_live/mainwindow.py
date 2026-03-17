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

from __future__ import annotations

import sys
from typing import Optional
import threading

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QLabel, QMainWindow, QMessageBox, QWidget
from PySide6.QtGui import QImage, QCloseEvent
from PySide6.QtCore import Qt, Slot, Signal

from ids_peak import ids_peak
from ids_peak_common import PixelFormat
import ids_peak_icv
from ids_peak_icv.pipeline import DefaultPipeline

from display import Display


TARGET_PIXEL_FORMAT = PixelFormat.BGRA_8


class MainWindow(QMainWindow):
    signal_image_acquired = Signal(QImage)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._widget = QWidget(self)
        self._layout = QVBoxLayout()
        self._widget.setLayout(self._layout)
        self.setCentralWidget(self._widget)

        self._device: Optional[ids_peak.Device] = None
        self._nodemap_remote_device: Optional[ids_peak.NodeMap] = None
        self._datastream: Optional[ids_peak.DataStream] = None

        self._worker_thread: Optional[threading.Thread] = None
        self.signal_image_acquired.connect(self._on_image_acquired)

        self._display = None
        self._frame_counter: int = 0
        self._error_counter: int = 0
        self._acquisition_running = False

        self._label_infos: Optional[QLabel] = None
        self._label_aboutqt: Optional[QLabel] = None

        # The library must be initialized before use.
        # Each `Initialize` call must be matched with a corresponding call
        # to `Close`.
        ids_peak.Library.Initialize()

        # Create an instance of the default pixel pipeline which defines a
        # sequence of processing steps that are applied to an acquired image.
        # The image is then processed into an image of the specified output
        # pixel format.
        self._image_pipeline = DefaultPipeline()
        self._image_pipeline.output_pixel_format = TARGET_PIXEL_FORMAT

        if self._open_device():
            try:
                # Create a display for the camera image
                self._display = Display()
                self._layout.addWidget(self._display)
                if not self._start_acquisition():
                    QMessageBox.critical(
                        self, "Error", "Unable to start acquisition!", QMessageBox.StandardButton.Ok
                    )
            except Exception as e:
                QMessageBox.critical(self, "Exception", str(e), QMessageBox.StandardButton.Ok)

        else:
            self._destroy_all()
            sys.exit(0)

        self._create_statusbar()

        self.setMinimumSize(700, 500)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Handles the QMainWindow close event
        """
        self._destroy_all()
        event.accept()

    def __del__(self) -> None:
        self._destroy_all()

    def _destroy_all(self) -> None:
        # Stop acquisition
        self._stop_acquisition()

        # Close device and peak library
        self._close_device()
        # Each `Initialize` call must be matched with a corresponding call
        # to `Close`.
        ids_peak.Library.Close()

    def _open_device(self) -> bool:
        """
        Opens the next openable device.

        :return: True if a device could be opened
        """
        try:
            # Get the instance of the device manager singleton.
            device_manager = ids_peak.DeviceManager.Instance()

            # Update the device manager.
            # When `Update` is called, it searches for all producer libraries
            # contained in the directories found in the official GenICam GenTL
            # environment variable GENICAM_GENTL{32/64}_PATH. It then opens all
            # found ProducerLibraries, their Systems, their Interfaces, and lists
            # all available DeviceDescriptors.
            device_manager.Update()

            # Return if no device was found.
            if device_manager.Devices().empty():
                QMessageBox.critical(
                    self, "Error", "No device found!", QMessageBox.StandardButton.Ok
                )
                return False

            # Open the first openable device in the managers device list.
            for device in device_manager.Devices():
                if device.IsOpenable():
                    self._device = device.OpenDevice(ids_peak.DeviceAccessType_Control)
                    break

            # Return if no device could be opened.
            if self._device is None:
                QMessageBox.critical(
                    self, "Error", "Device could not be opened!", QMessageBox.StandardButton.Ok
                )
                return False

            # Open standard data stream
            datastreams = self._device.DataStreams()
            if datastreams.empty():
                QMessageBox.critical(
                    self, "Error", "Device has no DataStream!", QMessageBox.StandardButton.Ok
                )
                self._device = None
                return False

            self._datastream = datastreams[0].OpenDataStream()

            # Retrieve the remote device's primary node map, which in GenICam represents
            # a hierarchical set of device parameters (features) such as exposure, gain,
            # and firmware info. The remote nodemap provides access to controls implemented
            # on the device itself, primarily following the GenICam Standard Feature
            # Naming Convention (SFNC), while also supporting custom nodes to accommodate
            # device-specific features.
            self._nodemap_remote_device = self._device.RemoteDevice().NodeMaps()[0]

            # To prepare for untriggered continuous image acquisition, load the default
            # user set if available and wait until execution is finished
            try:
                self._nodemap_remote_device.FindNode("UserSetSelector").SetCurrentEntry("Default")
                self._nodemap_remote_device.FindNode("UserSetLoad").Execute()
                self._nodemap_remote_device.FindNode("UserSetLoad").WaitUntilDone()
            except ids_peak.Exception:
                # Userset is not available
                pass

            # Get the payload size for correct buffer allocation
            payload_size = self._nodemap_remote_device.FindNode("PayloadSize").Value()

            # Get minimum number of buffers that must be announced
            buffer_count_max = self._datastream.NumBuffersAnnouncedMinRequired()

            # Allocate and announce image buffers and queue them
            for _ in range(buffer_count_max):
                # Let the TL allocate the buffers.
                buffer = self._datastream.AllocAndAnnounceBuffer(payload_size)
                # Put the buffer in the pool.
                self._datastream.QueueBuffer(buffer)

            return True
        except ids_peak.Exception as e:
            QMessageBox.critical(self, "Exception", str(e), QMessageBox.StandardButton.Ok)

        return False

    def _close_device(self) -> None:
        """
        Stop acquisition if still running and close datastream and nodemap of the device
        """
        # Stop Acquisition in case it is still running
        self._stop_acquisition()

        # If a datastream has been opened, try to revoke its image buffers
        if self._datastream is not None:
            try:
                for buffer in self._datastream.AnnouncedBuffers():
                    self._datastream.RevokeBuffer(buffer)
            except Exception as e:
                QMessageBox.information(self, "Exception", str(e), QMessageBox.StandardButton.Ok)

    def _start_acquisition(self) -> bool:
        """
        Start Acquisition on camera and start the acquisition timer to receive and display images

        :return: True if acquisition start was successful
        """
        # Check that a device is opened and that the acquisition is NOT running. If not, return.
        if self._device is None or self._nodemap_remote_device is None or self._datastream is None:
            return False
        if self._acquisition_running:
            return True

        # Sets the target frame rate or maximum if target frame rate is to high
        target_fps = 30
        try:
            max_fps = self._nodemap_remote_device.FindNode("AcquisitionFrameRate").Maximum()
            target_fps = min(max_fps, target_fps)
            self._nodemap_remote_device.FindNode("AcquisitionFrameRate").SetValue(target_fps)
        except ids_peak.Exception:
            # `AcquisitionFrameRate` is not available. Unable to limit fps.
            # Print warning and continue.
            QMessageBox.warning(
                self,
                "Warning",
                "Unable to limit fps, since the AcquisitionFrameRate Node is"
                " not supported by the connected camera. Program will continue without limit.",
            )
            return False

        try:
            # Lock writable nodes, which could influence the payload size or
            # similar information during acquisition.
            self._nodemap_remote_device.FindNode("TLParamsLocked").SetValue(1)

            # Start acquisition both locally and on device.
            self._datastream.StartAcquisition()
            self._nodemap_remote_device.FindNode("AcquisitionStart").Execute()
            self._nodemap_remote_device.FindNode("AcquisitionStart").WaitUntilDone()
        except Exception as e:
            print("Exception: " + str(e))
            return False

        # Start the acquisition worker
        self._worker_thread = threading.Thread(target=self._acquisition_worker, daemon=True)
        self._worker_thread.start()

        self._acquisition_running = True

        return True

    def _stop_acquisition(self) -> None:
        """
        Stop acquisition worker and stop acquisition on camera
        """
        # Check that a device is opened and that the acquisition is running. If not, return.
        if (
            self._device is None
            or self._nodemap_remote_device is None
            or self._datastream is None
            or self._worker_thread is None
            or not self._acquisition_running
        ):
            return

        # Otherwise try to stop acquisition
        try:
            self._nodemap_remote_device.FindNode("AcquisitionStop").Execute()

            # Stop and flush the `DataStream`.
            # `KillWait` will cancel pending `WaitForFinishedBuffer` calls.
            # NOTE: One call to `KillWait` will cancel one pending `WaitForFinishedBuffer`.
            #       For more information, refer to the documentation of `KillWait`.
            self._datastream.KillWait()
            self._datastream.StopAcquisition(ids_peak.AcquisitionStopMode_Default)

            # Wait for the acquisition worker thread to finish
            self._worker_thread.join()

            # Discard all buffers from the acquisition engine.
            # They remain in the announced buffer pool.
            self._datastream.Flush(ids_peak.DataStreamFlushMode_DiscardAll)

            # Unlock parameters after acquisition stop
            if self._nodemap_remote_device is not None:
                try:
                    self._nodemap_remote_device.FindNode("TLParamsLocked").SetValue(0)
                except Exception as e:
                    QMessageBox.information(
                        self, "Exception", str(e), QMessageBox.StandardButton.Ok
                    )
            self._acquisition_running = False

        except Exception as e:
            QMessageBox.information(self, "Exception", str(e), QMessageBox.StandardButton.Ok)

    def _create_statusbar(self) -> None:
        status_bar = QWidget(self.centralWidget())
        status_bar_layout = QHBoxLayout()
        status_bar_layout.setContentsMargins(0, 0, 0, 0)

        self._label_infos = QLabel(status_bar)
        self._label_infos.setAlignment(Qt.AlignmentFlag.AlignLeft)
        status_bar_layout.addWidget(self._label_infos)
        status_bar_layout.addStretch()

        self._label_aboutqt = QLabel(status_bar)
        self._label_aboutqt.setObjectName("aboutQt")
        self._label_aboutqt.setText("<a href='#aboutQt'>About Qt</a>")
        self._label_aboutqt.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._label_aboutqt.linkActivated.connect(self._on_aboutqt_link_activated)
        status_bar_layout.addWidget(self._label_aboutqt)
        status_bar.setLayout(status_bar_layout)

        self._layout.addWidget(status_bar)

    def _update_counters(self) -> None:
        """
        This function gets called when the frame and error counters have changed
        """
        if self._label_infos:
            self._label_infos.setText(
                "Acquired: " + str(self._frame_counter) + ", Errors: " + str(self._error_counter)
            )

    def _acquisition_worker(self) -> None:
        """
        The acquisition worker is called from another context.
        It waits for new buffers to arrive, processes them with the image pipeline
        and converts them to a QImage.
        """
        if self._datastream is None:
            return

        while True:
            try:
                # Get buffer from device's datastream
                buffer = self._datastream.WaitForFinishedBuffer(ids_peak.Timeout(5000))

                # Convert the acquired buffer to an image view.
                # The ImageView defines a standard way to access image properties and raw pixel
                # data, enabling interoperability with different image processing libraries or
                # backends.
                # Note: This object does not own the image memory.
                image_view = buffer.ToImageView()

                # Pass the ImageView through the image pipeline which runs all processing steps
                # in sequence. The resulting image is guaranteed to be a copy.
                converted_image = self._image_pipeline.process(image_view)

                # Queue buffer so that it can be used again.
                self._datastream.QueueBuffer(buffer)

                # Get raw image data from converted image and construct a QImage from it.
                data = converted_image.to_numpy_array().data
                image = QImage(
                    data, converted_image.width, converted_image.height, QImage.Format.Format_RGB32
                )

                # Make an explicit copy of the QImage to ensure the underlying
                # image data is owned by Qt.
                # Without this, the QImage may reference memory managed by the
                # image library, which could be released or overwritten later.
                image_copy = image.copy()

                # Emit signal that the image is ready to be displayed
                self.signal_image_acquired.emit(image_copy)

                # Increase frame counter
                self._frame_counter += 1
            except ids_peak.TimeoutException:
                # There was no buffer received with in the provided timeout.
                # Retry again.
                pass
            except ids_peak.AbortedException:
                # Acquisition was aborted by calling DataStream.KillWait
                return
            except ids_peak.Exception as e:
                self._error_counter += 1
                print("Exception: " + str(e))

    @Slot(QImage)
    def _on_image_acquired(self, image: ids_peak_icv.datatypes.Image) -> None:
        # Emit signal that the image is ready to be displayed
        if self._display:
            self._display.on_image_received(image)
            self._display.update()

        # Update counters
        self._update_counters()

    @Slot(str)
    def _on_aboutqt_link_activated(self, link: str) -> None:
        if link == "#aboutQt":
            QMessageBox.aboutQt(self, "About Qt")
