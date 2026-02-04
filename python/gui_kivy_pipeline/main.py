# Copyright (C) 2025, IDS Imaging Development Systems GmbH.
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
This demo demonstrates how to use the ids_peak_icv default pipeline
together with the ids_peak_afl auto-feature module.

All device-specific behavior, such as setting exposure, framerate, and
supported pixel formats, is encapsulated in camera.py.

The ``DefaultPipelineSample`` class focuses on building the user interface
and interacting directly with the default pipeline.
``DefaultPipeline`` provides convenient properties for adjusting pipeline
settings such as output pixel format, host gain, binning, and more.

Custom widgets used by this sample are defined in custom_widgets.py.
"""

import threading
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import Any, cast, TypeVar

import kivy
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics.texture import Texture  # type: ignore
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.layout import Layout
from kivy.uix.widget import Widget
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.fitimage import FitImage
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.tab import MDTabsCarousel
from kivymd.uix.tab.tab import MDTabsItem, MDTabsItemText, MDTabsPrimary
from ids_peak_common import CommonException, PixelFormat, Range, Size
from ids_peak_icv import Image, Rotation
from ids_peak_icv.pipeline import DefaultPipeline
from plyer import filechooser
from ids_peak import ids_peak

from ids_peak_afl.pipeline import BasicAutoFeatures
from ids_peak_afl.pipeline.modules import ControllerMode
from ids_peak_afl.pipeline.modules.controllers.basic_auto_brightness import (
    AutoBrightnessPolicy,
)
from camera import Camera
from custom_widgets import (
    BackgroundLayout,
    CustomButton,
    FloatInput,
    MDSpinnerSelector,
    TextSlider,
    ToggleButton,
    bind_text_size_left,
    show_status_message,
)

kivy.require("2.3.0")
config = cast(kivy.config.ConfigParser, kivy.config.Config)
config.set("input", "mouse", "mouse,disable_multitouch")
config.set("kivy", "pause_on_minimize", 1)
config.set("kivy", "desktop", 1)

SIDEPANEL_SIZE = 450

T = TypeVar("T")


def not_none(x: T | None) -> Any:
    assert x is not None
    return x


@dataclass
class ProcessedImage:
    img: Image
    source_pixel_format: PixelFormat
    source_size: Size
    frame_id: int


class DefaultPipelineSample(MDApp):
    auto_brightness_policy_mapping = {
        "Exposure and gain": AutoBrightnessPolicy.EXPOSURE_AND_GAIN,
        "Exposure Only": AutoBrightnessPolicy.EXPOSURE_ONLY,
        "Gain Only": AutoBrightnessPolicy.GAIN_ONLY,
    }

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        Window.minimum_width = 800
        Window.minimum_height = 600
        Window.size = (1280, 1024)
        Window.bind(on_request_close=self.on_close_requested)

        # These are all widgets created later in build()
        self.camera_frame_rate: TextSlider | None = None
        self.camera_exposure: TextSlider | None = None
        self.camera_gain_selector: MDSpinnerSelector | None = None
        self.camera_gain: TextSlider | None = None
        self.camera_focus_stepper: TextSlider | None = None
        self.reset_camera_default: CustomButton | None = None

        self.input_pixel_format: MDSpinnerSelector | None = None
        self.conversion_label: MDLabel | None = None
        self.frame_id: MDLabel | None = None
        self.layout: MDBoxLayout | None = None

        self.binning_x: MDSpinnerSelector | None = None
        self.binning_y: MDSpinnerSelector | None = None
        self.decimation_x: MDSpinnerSelector | None = None
        self.decimation_y: MDSpinnerSelector | None = None

        self.mirror_x: MDCheckbox | None = None
        self.mirror_y: MDCheckbox | None = None
        self.rotate: MDSpinnerSelector | None = None

        self.gain_master: TextSlider | None = None
        self.gain_red: TextSlider | None = None
        self.gain_green: TextSlider | None = None
        self.gain_blue: TextSlider | None = None

        self.matrix: Any = None
        self.matrix_elements: list[FloatInput] = []
        self.saturation: TextSlider | None = None

        self.gamma: TextSlider | None = None
        self.digital_black: TextSlider | None = None

        self.sharpen: TextSlider | None = None

        self.save_button: CustomButton | None = None
        self.load_button: CustomButton | None = None
        self.reset_button: CustomButton | None = None

        # Auto brightness controls
        self.auto_brightness_toggle: ToggleButton | None = None
        self.policy_spinner: MDSpinnerSelector | None = None
        self.exposure_label: MDLabel | None = None
        self.master_gain_label: MDLabel | None = None

        # Auto white balance controls
        self.auto_white_balance_toggle: ToggleButton | None = None
        self.color_gain_label: MDLabel | None = None

        # Auto focus controls
        self.auto_focus_toggle: ToggleButton | None = None
        self.focus_stepper_label: MDLabel | None = None

        self.image_widget: FitImage | None = None

        # Create the camera class and start the acquisition.
        # The camera class is a thin wrapper around the ids_peak package.
        self.camera = Camera()
        self.camera.start_acquisition()

        # Set the window title to indicate which camera is open
        self.title = (
            f"{str(self.__class__.__name__)} - {self.camera.device.ModelName()} "
            f"({self.camera.device.SerialNumber()})"
        )

        # The autofeature module must be created first as it needs the opened
        # device for it to operate.
        # Note that the auto features are set to off by default.
        self.autofeature_module = BasicAutoFeatures(self.camera.device)

        # Create the default pipeline in its default state.
        # We set the ``autofeature_module`` property in the pipeline
        # to associate the autofeature module with it.
        # Without this step, the autofeature module would not automatically
        # receive any input images.
        self.pipeline = DefaultPipeline()
        self.pipeline.autofeature_module = self.autofeature_module

        # Create the Acquisition / Pipeline thread which processes the camera image.
        self.process_queue: Queue[ProcessedImage] = Queue()
        self.worker_thread = threading.Thread(target=self.pipeline_worker, daemon=True)
        self.worker_thread.start()

    def on_close_requested(self, _: Any) -> None:
        # Stop the WaitForFrame call.
        self.camera.kill_datastream_wait()

        # Stop the Acquisition and discard all buffers.
        self.camera.stop_acquisition()

        # Reset the image flip. This is needed for applications which may run after this sample.
        self.camera.restore_coordinate_flip()

        # Close the camera
        del self.camera

    def update_exposure_label(self) -> None:
        try:
            exposure = self.camera.exposure
            cast(MDLabel, self.exposure_label).text = f"Exposure: {exposure:.2f} us"
            slider = cast(TextSlider, self.camera_exposure)
            if self.autofeature_module.auto_brightness.mode != ControllerMode.OFF:
                slider.disabled = True
            else:
                slider.value = exposure
                slider.disabled = False
        except CommonException:
            pass

    def update_master_gain_label(self) -> None:
        assert self.master_gain_label is not None
        assert self.camera_gain is not None
        assert self.gain_master is not None

        try:
            value = self.camera.master_gain
            self.master_gain_label.text = f"Camera master gain: {value:.2f}x"

            awb_on = self.autofeature_module.auto_brightness.mode != ControllerMode.OFF
            self.camera_gain.disabled = awb_on
        except CommonException:
            pass
        except StopIteration:
            value = self.pipeline.gain.master
            self.master_gain_label.text = f"Host master gain: {value:.2f}x"
            self.gain_master.value = value

    def update_color_gain_label(self) -> None:
        values = []
        assert self.color_gain_label is not None

        try:
            for color in ["red", "green", "blue"]:
                value = getattr(self.camera, color + "_gain")
                values.append(value)

            self.color_gain_label.text = (
                f"Camera color gains (R/G/B):\n{values[0]:.2f} / {values[1]:.2f} / {values[2]:.2f}"
            )
        except (CommonException, UnicodeDecodeError):
            pass
        except StopIteration:
            for color in ["red", "green", "blue"]:
                value = getattr(self.pipeline.gain, color)
                values.append(value)
                getattr(self, "gain_" + color).value = value

            self.color_gain_label.text = (
                f"Host color gains (R/G/B):\n{values[0]:.2f} / {values[1]:.2f} / {values[2]:.2f}"
            )

    def update_focus_stepper_label(self) -> None:
        assert self.focus_stepper_label is not None
        assert self.camera_focus_stepper is not None

        if self.camera.has_focus_stepper:
            try:
                self.focus_stepper_label.text = f"Focus step: {self.camera.focus_stepper}"
                self.camera_focus_stepper.value = self.camera.focus_stepper
                self.camera_focus_stepper.range = self.camera.focus_stepper_range
                if self.autofeature_module.has_auto_focus:
                    self.camera_focus_stepper.disabled = (
                        self.autofeature_module.auto_focus.mode != ControllerMode.OFF
                    )
            except CommonException:
                pass

    def update_camera_frame_rate(self) -> None:
        assert self.camera_frame_rate is not None

        try:
            self.camera_frame_rate.value = self.camera.framerate
            self.camera_frame_rate.range = self.camera.framerate_range
        except CommonException:
            pass

    def update_camera_gain(self) -> None:
        assert self.camera_gain_selector is not None
        assert self.camera_gain is not None

        try:
            gain_value, gain_range = self.camera.get_gain(self.camera_gain_selector.text)
            self.camera_gain.value = gain_value
            self.camera_gain.range = gain_range
        except CommonException:
            pass

    def update_input_pixel_format(self) -> None:
        assert self.input_pixel_format is not None

        try:
            pixel_format_str = str(self.camera.pixel_format)
            if pixel_format_str != self.input_pixel_format.text:
                self.input_pixel_format.text = pixel_format_str
        except CommonException:
            pass

    def update_all_labels(self, _: Any) -> None:
        self.update_input_pixel_format()
        self.update_camera_frame_rate()
        self.update_exposure_label()
        self.update_master_gain_label()
        self.update_camera_gain()
        if self.autofeature_module.has_auto_white_balance:
            self.update_color_gain_label()
        if self.autofeature_module.has_auto_focus:
            self.update_focus_stepper_label()

    def on_auto_brightness_toggle_press(self, toggle: ButtonBehavior) -> None:
        self.autofeature_module.auto_brightness.mode = (
            ControllerMode.CONTINUOUS if (toggle.state == "down") else ControllerMode.OFF
        )

    def on_auto_brightness_policy_spinner_changed(self, _: Any, text: str) -> None:
        try:
            self.autofeature_module.auto_brightness.policy = self.auto_brightness_policy_mapping[
                text
            ]
        except CommonException as exc:
            show_status_message("Failed", f"Failed to set auto brightness policy:\n{exc}")

    def on_auto_white_balance_toggle_press(self, toggle: ButtonBehavior) -> None:
        try:
            self.autofeature_module.auto_white_balance.mode = (
                ControllerMode.CONTINUOUS if (toggle.state == "down") else ControllerMode.OFF
            )
        except CommonException as exc:
            show_status_message("Failed", f"Failed to set auto white balance:\n{exc}")

    def on_auto_focus_toggle_press(self, toggle: ButtonBehavior) -> None:
        try:
            self.autofeature_module.auto_focus.mode = (
                ControllerMode.CONTINUOUS if (toggle.state == "down") else ControllerMode.OFF
            )
        except CommonException as exc:
            show_status_message("Failed", f"Failed to set auto focus:\n{exc}")

    def on_pixel_format_changed(self, _: Any, text: str) -> None:
        pixel_format = getattr(PixelFormat, text)
        try:
            self.camera.pixel_format = pixel_format
        except CommonException as exc:
            show_status_message("Failed", f"Failed to set Pixel Format:\n{exc}")

    def save_file(self, _: Any) -> None:
        file_filters = [("JSON Files", "*.json"), ("All Files", "*.*")]
        try:
            filechooser.save_file(
                filters=file_filters,
                filename="pipeline_config.json",
                on_selection=self.handle_save_selection,
            )
        except (OSError, NotImplementedError):
            show_status_message(
                "Failed",
                "No native FileChooser interface available.\n"
                "Please install one after consulting either the README.md or "
                "the plyer FileChooser documentation!",
            )

    def handle_save_selection(self, selection: list[str]) -> None:
        if selection:
            save_path = selection[0]
            try:
                if Path(save_path).suffix == "":
                    save_path += ".json"

                self.pipeline.export_settings_to_file(save_path)
                show_status_message(
                    "File saved", f"The settings were written to the file {save_path}"
                )
            except Exception as e:
                show_status_message("Failed", str(e))

    def load_file(self, _: Any) -> None:
        file_filters = [("JSON Files", "*.json"), ("All Files", "*.*")]
        try:
            filechooser.open_file(
                filters=file_filters,
                filename="pipeline_config.json",
                on_selection=self.handle_load_selection,
            )
        except (OSError, NotImplementedError):
            show_status_message(
                "Failed",
                "No native FileChooser interface available.\n"
                "Please install one after consulting either the README.md or "
                "the plyer FileChooser documentation!",
            )

    def handle_load_selection(self, selection: list[str]) -> None:
        if selection:
            load_path = selection[0]
            try:
                self.pipeline.import_settings_from_file(load_path)
                self.update_pipeline_settings()
            except Exception as e:
                traceback.print_exc()
                show_status_message("Failed", str(e))

    def on_matrix_edited(self, instance: Widget, text: str) -> None:
        try:
            matrix = self.pipeline.color_correction.matrix.flatten()
            matrix[instance.index] = float(text)
            self.pipeline.color_correction.matrix = matrix.reshape((3, 3))
        except CommonException as exc:
            show_status_message("Failed", f"Failed to set matrix value:\n{exc}")
        except ValueError:
            pass

    def on_matrix_focus(self, instance: Widget, value: bool) -> None:
        # check for focus lost
        if not value:
            matrix = self.pipeline.color_correction.matrix.flatten()
            instance.text = str(matrix[instance.index])

    def update_pipeline_settings(self) -> None:
        # After loading a JSON file or pipeline reset, we need to update
        # the state of all controls

        not_none(self.auto_brightness_toggle).state = (
            "down"
            if (self.autofeature_module.auto_brightness.mode == ControllerMode.CONTINUOUS)
            else "normal"
        )
        keys = list(
            filter(
                lambda key: (
                    self.auto_brightness_policy_mapping[key]
                    == self.autofeature_module.auto_brightness.policy
                ),
                self.auto_brightness_policy_mapping,
            )
        )
        not_none(self.policy_spinner).text = keys[0]

        if self.autofeature_module.has_auto_white_balance:
            not_none(self.auto_white_balance_toggle).state = (
                "down"
                if (self.autofeature_module.auto_white_balance.mode == ControllerMode.CONTINUOUS)
                else "normal"
            )

        if self.autofeature_module.has_auto_focus:
            not_none(self.auto_focus_toggle).state = (
                "down"
                if (self.autofeature_module.auto_focus.mode == ControllerMode.CONTINUOUS)
                else "normal"
            )

        not_none(self.decimation_x).text = str(self.pipeline.decimation.x)
        not_none(self.decimation_y).text = str(self.pipeline.decimation.y)
        not_none(self.binning_x).text = str(self.pipeline.binning.x)
        not_none(self.binning_y).text = str(self.pipeline.binning.y)

        not_none(self.mirror_x).active = self.pipeline.mirror.left_right_enabled
        not_none(self.mirror_y).active = self.pipeline.mirror.up_down_enabled
        not_none(self.rotate).text = str(self.pipeline.rotation.angle.value)

        not_none(self.gain_master).value = float(self.pipeline.gain.master)
        not_none(self.gain_red).value = float(self.pipeline.gain.red)
        not_none(self.gain_green).value = float(self.pipeline.gain.green)
        not_none(self.gain_blue).value = float(self.pipeline.gain.blue)

        matrix = self.pipeline.color_correction.matrix.flatten()
        for el in self.matrix_elements:
            el.text = str(matrix[el.index])
        not_none(self.saturation).value = float(self.pipeline.saturation.value)

        not_none(self.sharpen).value = int(self.pipeline.sharpening.level)
        not_none(self.gamma).value = float(self.pipeline.gamma.value)
        not_none(self.digital_black).value = float(self.pipeline.digital_black.value)

    def on_gain_selector_changed(self, value: str) -> None:
        assert self.camera_gain is not None

        try:
            gain_value, gain_range = self.camera.get_gain(value)
            self.camera_gain.range = gain_range
            self.camera_gain.value = gain_value
        except CommonException as exc:
            show_status_message("Failed", f"Failed to set gain selector:\n{exc}")

    def reset_pipeline(self, _: Any) -> None:
        """
        Reset the pipeline to its default state.
        Afterward, update all settings.
        """
        try:
            self.pipeline.reset_to_default()
            self.update_pipeline_settings()
        except CommonException as exc:
            show_status_message("Failed", f"Failed to update pipeline settings:\n{exc}")

    def set_camera_attr(self, name: str, value: Any) -> None:
        try:
            setattr(self.camera, name, value)
        except CommonException as exc:
            show_status_message("Failed", f"Failed to set camera attribute {name}:\n{exc}")

    @staticmethod
    def call_function(func: Callable, *args: Any, **kwargs: Any) -> None:
        try:
            func(*args, **kwargs)
        except CommonException as exc:
            show_status_message("Failed", f"Failed to call function:\n{exc}")

    @staticmethod
    def set_proportional_widths(grid: MDGridLayout) -> None:
        for i, child in enumerate(grid.children[::-1]):  # children are reversed
            if isinstance(child, MDCheckbox):
                continue
            if i % 2 == 0:  # first column
                child.size_hint_x = 1
            else:  # second column
                child.size_hint_x = 2

    def build_pipeline_tab(self) -> MDBoxLayout:
        settings_tab = MDBoxLayout(padding=[10, 10, 10, 10], size_hint_x=None, width=SIDEPANEL_SIZE)

        scroll_view = MDScrollView(
            size_hint_x=None, width=SIDEPANEL_SIZE, size_hint_y=1, do_scroll_x=False
        )

        control_panel = MDGridLayout(
            cols=2,
            spacing=10,
            size_hint_x=None,
            width=SIDEPANEL_SIZE,
            size_hint_y=None,
            padding=[10, 10, 10, 10],
        )
        control_panel.bind(minimum_height=control_panel.setter("height"))

        # --- Auto Brightness ---

        control_panel.add_widget(
            bind_text_size_left(MDLabel(text="Auto brightness:", halign="left"))
        )

        self.auto_brightness_toggle = ToggleButton(text_on="Continuous", text_off="Off")
        self.auto_brightness_toggle.bind(on_press=self.on_auto_brightness_toggle_press)
        control_panel.add_widget(self.auto_brightness_toggle)

        control_panel.add_widget(
            bind_text_size_left(MDLabel(text="Auto brightness policy:", halign="left"))
        )
        self.policy_spinner = MDSpinnerSelector(
            text="Exposure and gain",
            values=("Exposure and gain", "Exposure Only", "Gain Only"),
        )
        keys = list(
            filter(
                lambda key: (
                    self.auto_brightness_policy_mapping[key]
                    == self.autofeature_module.auto_brightness.policy
                ),
                self.auto_brightness_policy_mapping,
            )
        )
        if len(keys) > 0:
            self.policy_spinner.text = keys[0]
        self.policy_spinner.bind(text=self.on_auto_brightness_policy_spinner_changed)
        control_panel.add_widget(self.policy_spinner)

        # --- Auto White Balance ---

        control_panel.add_widget(
            bind_text_size_left(MDLabel(text="Auto white balance:", halign="left"))
        )
        self.auto_white_balance_toggle = ToggleButton(text_on="Continuous", text_off="Off")
        if self.autofeature_module.has_auto_white_balance:
            self.auto_white_balance_toggle.bind(on_press=self.on_auto_white_balance_toggle_press)
        else:
            self.auto_white_balance_toggle.disabled = True
        control_panel.add_widget(self.auto_white_balance_toggle)

        # --- Auto Focus ---

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Auto focus:")))
        self.auto_focus_toggle = ToggleButton(text_on="Continuous", text_off="Off")
        if self.autofeature_module.has_auto_focus:
            self.auto_focus_toggle.bind(on_press=self.on_auto_focus_toggle_press)
        else:
            self.auto_focus_toggle.disabled = True
        control_panel.add_widget(self.auto_focus_toggle)

        # --- Binning ---
        control_panel.add_widget(bind_text_size_left(MDLabel(text="Binning X:")))
        binning_range = self.pipeline.binning.range
        binning_text = [
            str(x) for x in range(int(binning_range.minimum), int(binning_range.maximum))
        ]
        self.binning_x = MDSpinnerSelector(
            text=str(self.pipeline.binning.x), values=binning_text, size_hint_x=2
        )
        self.binning_x.bind(
            text=lambda _, x: self.call_function(setattr, self.pipeline.binning, "x", int(x))
        )
        control_panel.add_widget(self.binning_x)

        control_panel.add_widget(
            bind_text_size_left(
                MDLabel(
                    text="Binning Y:",
                )
            )
        )
        self.binning_y = MDSpinnerSelector(text=str(self.pipeline.binning.y), values=binning_text)
        self.binning_y.bind(
            text=lambda _, x: self.call_function(setattr, self.pipeline.binning, "y", int(x))
        )
        control_panel.add_widget(self.binning_y)

        # --- Decimation ---

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Decimation X:")))
        decimation_range = self.pipeline.decimation.range
        decimation_text = [
            str(x) for x in range(int(decimation_range.minimum), int(decimation_range.maximum))
        ]
        self.decimation_x = MDSpinnerSelector(
            text=str(self.pipeline.decimation.x), values=decimation_text
        )
        self.decimation_x.bind(
            text=lambda _, x: self.call_function(setattr, self.pipeline.decimation, "x", int(x))
        )
        control_panel.add_widget(self.decimation_x)

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Decimation Y:")))
        self.decimation_y = MDSpinnerSelector(
            text=str(self.pipeline.decimation.y), values=decimation_text
        )
        self.decimation_y.bind(
            text=lambda _, x: self.call_function(setattr, self.pipeline.decimation, "y", int(x))
        )
        control_panel.add_widget(self.decimation_y)

        # --- Transform ---

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Mirror X:")))

        self.mirror_x = MDCheckbox(active=self.pipeline.mirror.left_right_enabled)
        self.mirror_x.bind(
            active=lambda _, x: self.call_function(
                setattr, self.pipeline.mirror, "left_right_enabled", x
            )
        )
        control_panel.add_widget(self.mirror_x)

        control_panel.add_widget(
            bind_text_size_left(
                MDLabel(
                    text="Mirror Y:",
                )
            )
        )

        self.mirror_y = MDCheckbox(active=self.pipeline.mirror.up_down_enabled)
        self.mirror_y.bind(
            active=lambda _, x: self.call_function(
                setattr, self.pipeline.mirror, "up_down_enabled", x
            )
        )
        control_panel.add_widget(self.mirror_y)

        control_panel.add_widget(
            bind_text_size_left(
                MDLabel(
                    text="Rotation:",
                )
            )
        )

        self.rotate = MDSpinnerSelector(
            text=str(self.pipeline.rotation.angle.value),
            values=("0", "90", "180", "270"),
        )
        self.rotate.bind(
            text=lambda _, x: self.call_function(
                setattr, self.pipeline.rotation, "angle", Rotation(int(x))
            )
        )
        control_panel.add_widget(self.rotate)

        # --- Gain ---

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Master Gain:")))

        gain_range = self.pipeline.gain.range
        self.gain_master = TextSlider(range_like=gain_range, value=self.pipeline.gain.master)
        self.gain_master.bind(
            value=lambda _, x: self.call_function(setattr, self.pipeline.gain, "master", float(x))
        )
        control_panel.add_widget(self.gain_master)

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Red Gain:")))

        self.gain_red = TextSlider(range_like=gain_range, value=self.pipeline.gain.red)
        self.gain_red.bind(
            value=lambda _, x: self.call_function(setattr, self.pipeline.gain, "red", float(x))
        )
        control_panel.add_widget(self.gain_red)

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Green Gain:")))

        self.gain_green = TextSlider(range_like=gain_range, value=self.pipeline.gain.green)
        self.gain_green.bind(
            value=lambda _, x: self.call_function(setattr, self.pipeline.gain, "green", float(x))
        )
        control_panel.add_widget(self.gain_green)

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Blue Gain:")))

        self.gain_blue = TextSlider(range_like=gain_range, value=self.pipeline.gain.blue)
        self.gain_blue.bind(
            value=lambda _, x: self.call_function(setattr, self.pipeline.gain, "blue", float(x))
        )
        control_panel.add_widget(self.gain_blue)

        # --- Color Correction

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Matrix:", halign="left")))

        matrix = self.pipeline.color_correction.matrix.flatten()
        matrix_grid = MDGridLayout(cols=3, spacing=10, size_hint_y=None)
        for i in range(9):
            el = FloatInput(text=str(matrix[i]))
            el.index = i
            el.bind(text=self.on_matrix_edited)
            el.bind(focus=self.on_matrix_focus)
            self.matrix_elements.append(el)
            matrix_grid.add_widget(el)
        control_panel.add_widget(matrix_grid)
        matrix_grid.bind(minimum_height=matrix_grid.setter("height"))

        saturation_range = self.pipeline.saturation.range

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Saturation:")))

        self.saturation = TextSlider(range_like=saturation_range, value=self.pipeline.gamma.value)
        self.saturation.bind(
            value=lambda _, x: self.call_function(
                setattr, self.pipeline.saturation, "value", float(x)
            )
        )
        control_panel.add_widget(self.saturation)

        # --- Tone curve ---

        gamma_range = self.pipeline.gamma.range
        digital_black_range = self.pipeline.digital_black.range

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Gamma:")))

        self.gamma = TextSlider(range_like=gamma_range, value=self.pipeline.gamma.value)
        self.gamma.bind(
            value=lambda _, x: self.call_function(setattr, self.pipeline.gamma, "value", float(x))
        )
        control_panel.add_widget(self.gamma)

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Digital Black:")))

        self.digital_black = TextSlider(
            range_like=digital_black_range, value=self.pipeline.digital_black.value
        )
        self.digital_black.bind(
            value=lambda _, x: self.call_function(
                setattr, self.pipeline.digital_black, "value", float(x)
            )
        )
        control_panel.add_widget(self.digital_black)

        # --- Sharpen ---

        control_panel.add_widget(
            bind_text_size_left(
                MDLabel(
                    text="Sharpen:",
                )
            )
        )

        sharpen_range = self.pipeline.sharpening.range

        self.sharpen = TextSlider(
            min=sharpen_range.minimum,
            max=sharpen_range.maximum,
            value=self.pipeline.sharpening.level,
        )
        self.sharpen.bind(
            value=lambda _, x: self.call_function(
                setattr, self.pipeline.sharpening, "level", int(x)
            )
        )
        control_panel.add_widget(self.sharpen)

        # --- The Stretcher ---

        control_panel.add_widget(Widget(size_hint_y=1))
        control_panel.add_widget(Widget(size_hint_y=1))

        self.set_proportional_widths(control_panel)

        scroll_view.add_widget(control_panel)
        settings_tab.add_widget(scroll_view)

        return settings_tab

    def build_camera_tab(self) -> MDBoxLayout:
        tab_camera = MDBoxLayout(orientation="vertical")
        scroll_view = MDScrollView(
            size_hint_x=None, width=SIDEPANEL_SIZE, size_hint_y=1, do_scroll_x=False
        )

        control_panel = MDGridLayout(
            cols=2,
            spacing=10,
            size_hint_x=None,
            width=SIDEPANEL_SIZE,
            size_hint_y=None,
            padding=[10, 10, 10, 10],
        )
        control_panel.bind(minimum_height=control_panel.setter("height"))

        # --- Input Pixel Format ---

        control_panel.add_widget(
            bind_text_size_left(MDLabel(text="Input pixel format:", halign="left"))
        )

        text_entries = [str(entry) for entry in self.camera.pixel_format_list]
        current_in_pixel_format = self.camera.pixel_format
        self.input_pixel_format = MDSpinnerSelector(
            text=str(current_in_pixel_format),
            values=text_entries,
        )
        self.input_pixel_format.bind(text=self.on_pixel_format_changed)
        control_panel.add_widget(self.input_pixel_format)

        # --- Framerate ---

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Framerate:")))

        self.camera_frame_rate = TextSlider(
            range_like=self.camera.framerate_range,
            value=self.camera.framerate,
        )
        self.camera_frame_rate.bind(value=lambda _, value: self.set_camera_attr("framerate", value))
        control_panel.add_widget(self.camera_frame_rate)

        # --- Exposure ---

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Exposure:")))

        self.camera_exposure = TextSlider(
            range_like=self.camera.exposure_range,
            value=self.camera.exposure,
        )
        self.camera_exposure.bind(value=lambda _, value: self.set_camera_attr("exposure", value))
        control_panel.add_widget(self.camera_exposure)

        # --- Gain ---

        entries = self.camera.gain_type_list()
        has_entries = len(entries) > 0
        gain_selector = entries[0] if has_entries else "n/a"

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Gain Selector:", halign="left")))
        self.camera_gain_selector = MDSpinnerSelector(
            text=gain_selector,
            values=entries,
        )
        self.camera_gain_selector.bind(text=lambda _, x: self.on_gain_selector_changed(x))
        self.camera_gain_selector.disabled = not has_entries
        control_panel.add_widget(self.camera_gain_selector)

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Gain:", halign="left")))
        gain_range = Range(0, 1, 0)
        gain_value = 0.0
        if has_entries:
            gain_value, gain_range = self.camera.get_gain(gain_selector)
        self.camera_gain = TextSlider(
            range_like=gain_range,
            value=gain_value,
        )
        self.camera_gain.bind(
            value=lambda _, value: self.call_function(
                self.camera.set_gain, self.camera_gain_selector.text, value
            )
        )
        self.camera_gain.disabled = not has_entries

        control_panel.add_widget(self.camera_gain)

        # --- Focus Stepper ---

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Focus stepper:")))

        has_af = self.camera.has_focus_stepper
        self.camera_focus_stepper = TextSlider(
            range_like=self.camera.focus_stepper_range if has_af else None,
            value=self.camera.focus_stepper if has_af else 0,
        )
        self.camera_focus_stepper.disabled = not has_af
        self.camera_focus_stepper.bind(
            value=lambda _, value: self.set_camera_attr("focus_stepper", int(value))
        )
        control_panel.add_widget(self.camera_focus_stepper)

        # --- Camera reset ---

        control_panel.add_widget(bind_text_size_left(MDLabel(text="Reset To Default:")))
        self.reset_camera_default = CustomButton(text="Execute")
        self.reset_camera_default.bind(
            on_press=lambda _: self.call_function(self.camera.reset_to_default)
        )
        control_panel.add_widget(self.reset_camera_default)

        self.set_proportional_widths(control_panel)

        scroll_view.add_widget(control_panel)
        tab_camera.add_widget(scroll_view)
        return tab_camera

    def build(self) -> Layout:
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primaryColor = "#008A96"

        self.layout = MDBoxLayout(orientation="vertical", padding=[10, 10, 10, 10], spacing=10)
        base_layout = MDBoxLayout(orientation="horizontal", spacing=10)

        settings_layout = MDBoxLayout(
            orientation="vertical",
            spacing=10,
            size_hint_x=None,
            width=SIDEPANEL_SIZE + 20,
            size_hint_y=1,
        )

        carousel = MDTabsCarousel()
        carousel.lock_swiping = True

        tab_bar = MDTabsPrimary(
            pos_hint={"center_x": 0.5, "center_y": 0.1}, size_hint_x=1, size_hint_y=1
        )
        tab_bar.lock_swiping = True
        tab_bar.label_only = True
        tab_bar.add_widget(carousel)

        tab_bar.add_widget(MDTabsItem(MDTabsItemText(text="Pipeline")))
        carousel.add_widget(self.build_pipeline_tab())

        tab_bar.add_widget(MDTabsItem(MDTabsItemText(text="Camera")))
        carousel.add_widget(self.build_camera_tab())

        settings_layout.add_widget(tab_bar)

        button_layout = MDBoxLayout(
            orientation="horizontal",
            padding=[10, 10, 10, 10],
            spacing=10,
            size_hint_y=None,
            height=65,
        )

        self.save_button = CustomButton(
            text="Save",
        )
        self.load_button = CustomButton(
            text="Load",
        )
        self.reset_button = CustomButton(
            text="Reset",
        )
        self.save_button.bind(on_press=self.save_file)
        self.load_button.bind(on_press=self.load_file)
        self.reset_button.bind(on_press=self.reset_pipeline)

        button_layout.add_widget(self.load_button)
        button_layout.add_widget(self.save_button)
        button_layout.add_widget(self.reset_button)

        settings_layout.add_widget(button_layout)

        base_layout.add_widget(settings_layout)

        # --- Image Widget ---

        image_layout = BackgroundLayout(
            orientation="horizontal", spacing=5, size_hint_x=1, size_hint_y=1
        )

        self.image_widget = FitImage(fit_mode="contain")
        image_layout.add_widget(self.image_widget)
        base_layout.add_widget(image_layout)

        self.layout.add_widget(base_layout)

        # --- Info Widgets ---

        row_value_labels = MDBoxLayout(
            orientation="horizontal", spacing=5, size_hint_y=None, height=45
        )

        self.frame_id = bind_text_size_left(
            MDLabel(text="Frame ID: n/a", size_hint_x=0.2, halign="left")
        )
        row_value_labels.add_widget(self.frame_id)

        self.exposure_label = bind_text_size_left(
            MDLabel(text="Exposure: ", size_hint_x=0.2, halign="left")
        )
        row_value_labels.add_widget(self.exposure_label)

        self.master_gain_label = bind_text_size_left(
            MDLabel(text="Master gain: ", size_hint_x=0.2, halign="left")
        )
        row_value_labels.add_widget(self.master_gain_label)

        if self.autofeature_module.has_auto_white_balance:
            self.color_gain_label = bind_text_size_left(
                MDLabel(
                    text="Host color gains (R/G/B): - / - / -",
                    size_hint_x=0.2,
                    halign="left",
                )
            )
            row_value_labels.add_widget(self.color_gain_label)

        if self.autofeature_module.has_auto_focus:
            self.focus_stepper_label = bind_text_size_left(
                MDLabel(text="Focus stepper: -", size_hint_x=0.2, halign="left")
            )
            row_value_labels.add_widget(self.focus_stepper_label)

        self.conversion_label = bind_text_size_left(
            MDLabel(text="Conversion Info: N/A to N/A", size_hint_x=0.2, halign="left")
        )
        row_value_labels.add_widget(self.conversion_label)

        self.layout.add_widget(row_value_labels)

        Clock.schedule_interval(self.update_all_labels, 1 / 10)
        Clock.schedule_interval(self.update_image, 1.0 / 30.0)

        return self.layout

    def pipeline_worker(self) -> None:
        while True:
            try:
                # Wait for the next available image from the camera.
                # We set a timeout of 1000 milliseconds here.
                image_view = self.camera.wait_for_image_view(1000)

                # Skip incomplete buffers and immediately re-queue them for reuse.
                if image_view.parent_buffer.IsIncomplete():
                    self.camera.queue_buffer(image_view.parent_buffer)
                    continue

                # Skip the image, if an image is already queued to be displayed
                if not self.process_queue.empty():
                    self.camera.queue_buffer(image_view.parent_buffer)
                    continue

                # copy relevant source infos
                source_pixel_format, source_size = (
                    image_view.pixel_format,
                    image_view.size,
                )
                frame_id = image_view.parent_buffer.FrameID()

                img = None
                try:
                    # Process the image through the pipeline.
                    # Autofeatures and all configured modules (conversion, debayering, etc.)
                    # are executed sequentially here.
                    img = self.pipeline.process(image_view)
                except CommonException as e:
                    # An error while processing the image occurred.
                    # Print the exception message and continue
                    print(f"Failed to process image: {e}")

                # The DefaultPipeline guarantees that the output image is a copy, therefore
                # the buffer can be re-queued.
                # Return the buffer to the API so it can be reused for future images.
                self.camera.queue_buffer(image_view.parent_buffer)

                # push the resulting image to the queue, so it can be displayed
                if img:
                    self.process_queue.put(
                        ProcessedImage(img, source_pixel_format, source_size, frame_id)
                    )

            except ids_peak.TimeoutException:
                # There was no buffer received with in the provided timeout.
                # Retry again.
                pass
            except ids_peak.AbortedException:
                # Acquisition was aborted by calling Datastream.KillWait
                return
            except CommonException:
                # May happen when the camera was disconnected, or some other error occurred
                pass

    def update_image(self, _: Any) -> None:
        """
        Generates the NumPy array, stores it, converts it to a Kivy texture,
        and updates the Image widget.
        """

        def get_texture(image: Image) -> Texture:
            # Although we configure RGB8 as the default output pixel format,
            # the application must still be capable of handling any supported pixel format.
            # This is necessary because configuration files can override the default
            # and provide their own format settings.
            #
            # If a configuration specifies a format we don’t properly support,
            # the image-to-texture conversion in Kivy may fail and trigger runtime errors.

            pixel_format = image.pixel_format
            numpy_data = image.to_numpy_array()

            if numpy_data.ndim == 1:
                # Either the user supplied a flattened numpy array or
                # an older ids_peak interface is used
                if pixel_format.is_single_channel:
                    numpy_data = numpy_data.reshape((image.height, image.width))
                else:
                    numpy_data = numpy_data.reshape(
                        (image.height, image.width, pixel_format.number_of_channels)
                    )

            # Check for 10/12-bit data and scale it
            if (
                pixel_format.storage_bits_per_channel == 12
                or pixel_format.storage_bits_per_channel == 10
            ):
                numpy_data = numpy_data.astype("uint16")
                numpy_data = numpy_data << (16 - pixel_format.storage_bits_per_channel)
                buffer_fmt = "ushort"
            elif pixel_format.storage_bits_per_channel == 16:
                buffer_fmt = "ushort"
            elif pixel_format.storage_bits_per_channel == 8:
                buffer_fmt = "ubyte"
            else:
                raise ValueError(f"Unsupported bit depth: {pixel_format.storage_bits_per_channel}")

            if pixel_format.is_single_channel:
                height, width = numpy_data.shape
                buf = numpy_data.tobytes()
                texture = Texture.create(size=(width, height), colorfmt="luminance")
                texture.blit_buffer(buf, colorfmt="luminance", bufferfmt=buffer_fmt)
                return texture
            else:
                height, width, channels = numpy_data.shape
                buf = numpy_data.tobytes()

                color_format = "".join(
                    [str(channel.name)[0].lower() for channel in pixel_format.channels]
                )

                texture = Texture.create(size=(width, height), colorfmt=color_format)
                texture.blit_buffer(buf, colorfmt=color_format, bufferfmt=buffer_fmt)
                return texture

        if not self.process_queue.empty():
            assert self.conversion_label is not None
            assert self.frame_id is not None
            assert self.image_widget is not None

            processed_image = self.process_queue.get()

            self.conversion_label.text = (
                f"Converted: {processed_image.source_pixel_format} "
                f"[{processed_image.source_size.width}x{processed_image.source_size.height}] "
                f"to {processed_image.img.pixel_format} "
                f"[{processed_image.img.size.width}x{processed_image.img.size.height}]"
            )
            self.frame_id.text = f"Frame ID: {processed_image.frame_id}"

            # Convert the processed image into a Kivy texture and display it.
            self.image_widget.texture = get_texture(processed_image.img)


if __name__ == "__main__":
    DefaultPipelineSample().run()
