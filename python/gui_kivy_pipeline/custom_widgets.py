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

from __future__ import annotations
import re
from typing import Any, Sequence, cast

from kivy.graphics import Rectangle, Color
from kivy.metrics import dp
from kivy.properties import (  # type: ignore
    ListProperty,
    BoundedNumericProperty,
    NumericProperty,
    StringProperty,
    BooleanProperty,
)
from kivy.uix.behaviors import ToggleButtonBehavior
from kivy.uix.widget import Widget
from kivymd.uix.behaviors import TouchBehavior

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.app import MDApp
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogHeadlineText,
    MDDialogSupportingText,
    MDDialogButtonContainer,
)
from kivymd.uix.label import MDLabel
from kivymd.uix.menu.menu import MDDropdownMenu
from kivymd.uix.slider import MDSlider, MDSliderHandle
from kivymd.uix.textfield import MDTextField
from ids_peak_common import Range, Interval


def bind_text_size_left(widget: Widget) -> Widget:
    """
    Helper function to bind size to text_size for left alignment.
    """
    # Use a lambda to ensure the binding happens when the widget size is known
    widget.bind(
        size=lambda instance, value: instance.setter("text_size")(instance, (instance.width, None))
    )
    return widget


class CustomButton(MDButton):
    text = StringProperty()

    def __init__(self, text: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.theme_width = "Custom"
        self.size_hint_x = 1
        self.style = "tonal"
        self.radius = dp(5)
        self.button_text = MDButtonText(text=text)
        self.add_widget(self.button_text)
        self.button_text.bind(text=self._on_text_changed)
        self.bind(text=self._on_text_property_changed)

    def _on_text_changed(self, _: Any, value: str) -> None:
        self.text = value

    def _on_text_property_changed(self, _: Any, value: str) -> None:
        self.button_text.text = value


# Note: Do not inherit from MDToggleButtonBehavior unless running kivymd 2.1 or later,
# as older versions will not work.
class ToggleButton(ToggleButtonBehavior, MDButton):  # type: ignore
    """
    A KivyMD 2.0+ Button that toggles between two states and displays
    text based on its state.
    """

    text_on = StringProperty("On")
    text_off = StringProperty("Off")
    checked = BooleanProperty(False)

    def __init__(self, text_on: str = "On", text_off: str = "Off", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.theme_width = "Custom"
        self.text_on = text_on
        self.text_off = text_off
        self.style = "tonal"
        self.size_hint_x = 1
        self.radius = dp(5)

        self.button_text = MDButtonText()
        self.add_widget(self.button_text)

        self.bind(
            state=self._update_text,
            text_on=self._update_text,
            text_off=self._update_text,
            checked=self._checked_changed,
        )
        self.checked = self.state == "down"
        self.button_text.text = self.text_on if self.checked else self.text_off
        self.style = "filled" if self.checked else "tonal"

    def _checked_changed(self, _: Any, check: bool) -> None:
        self.state = "down" if check else "normal"

    def _update_text(self, *args: Any) -> None:
        """
        Updates the text based on the current 'active' state.
        """
        if self.state == "down" and not self.disabled:
            self.button_text.text = self.text_on
            self.checked = True
            self.style = "filled"
        else:
            self.button_text.text = self.text_off
            self.checked = False
            self.style = "tonal"


class CustomMenu(MDDropdownMenu):
    def on_open(self) -> None:
        pass


class MDSpinnerSelector(CustomButton):
    """
    A KivyMD widget that mimics the standard Kivy Spinner's functionality.
    """

    values = ListProperty([])

    _menu: None | MDDropdownMenu = None

    def __init__(
        self, text: None | str = None, values: None | Sequence[str] = None, **kwargs: Any
    ) -> None:
        super().__init__(text=text if text else "", **kwargs)
        self.bind(on_release=self.show_selection_menu)
        if values:
            self.values = values
            self.button_text.text = text or values[0]

    def on_values(self, _: Any, values: list[str]) -> None:
        """
        Called when the 'values' list is set or changed.
        """
        self._create_menu(values)
        if values and not self.text:
            self.text = values[0]

    def _create_menu(self, items: list[str]) -> None:
        """
        Internal method to generate the MDMenu instance using current KivyMD syntax.
        """

        menu_items_data = [
            {
                "text": item,
                "on_release": lambda x=item: self._handle_selection(x),
            }
            for item in items
        ]

        if self._menu:
            self._menu.dismiss()

        self._menu = CustomMenu(
            caller=self,
            position="bottom",
        )

        self._menu.items = menu_items_data
        self._menu.show_duration = 0
        self._menu.hide_duration = 0

    def _handle_selection(self, selected_text: str) -> None:
        """
        Called when an item in the MDMenu is tapped.
        """
        self.text = selected_text
        if self._menu:
            self._menu.dismiss()

    def show_selection_menu(self, _: Any) -> None:
        """Called when the MDTextField gains or loses focus."""
        if self._menu:
            self._menu.open()
            self._menu._scale_x = 1
            self._menu._scale_y = 1


class FloatInput(MDTextField):
    pat = re.compile(r"[^0-9.\-]")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.mode = "outlined"

    def insert_text(self, substring: str, from_undo: bool = False) -> None:
        s = substring

        # Handle minus sign
        if "-" in s:
            # Only allow minus at the start, and only if no minus already
            if self.cursor_index() != 0 or "-" in self.text:
                s = s.replace("-", "")
            else:
                s = "-"  # allow single minus at start

        # Handle decimal point
        if "." in s:
            if "." in self.text:
                # already has a dot, remove extra dots from substring
                s = s.replace(".", "")
            else:
                # allow only the first dot
                parts = s.split(".", 1)
                s = parts[0] + "." + re.sub(r"\.", "", parts[1]) if len(parts) > 1 else parts[0]

        # Remove any other invalid characters
        s = re.sub(self.pat, "", s)

        super().insert_text(s, from_undo=from_undo)


class InstantMDSliderHandle(MDSliderHandle):
    def on_enter(self) -> None:
        """
        Fired when mouse enter the bbox of the widget.
        Changes the display of the slider handle layer instantaneously.
        """

        if self._slider:
            if self._state_layer and not self._slider.disabled:
                self._active = True
                self._state_layer.scale_value_x = 1
                self._state_layer.scale_value_y = 1
                self._slider._update_state_layer_pos(
                    None, None
                )  # Call the completion method directly

            if not self._slider.disabled:
                self._slider.on_handle_enter()

    def on_leave(self) -> None:
        """
        Fired when the mouse goes outside the widget border.
        Changes the hiding of the slider handle layer instantaneously.
        """

        if self._slider:
            if self._state_layer and not self._slider.disabled:
                self._active = False
                self._state_layer.scale_value_x = 0
                self._state_layer.scale_value_y = 0
                self._slider._update_state_layer_pos(
                    None, None
                )  # Call the completion method directly

            if not self._slider.disabled:
                self._slider.on_handle_leave()


class SliderWithRelease(MDSlider):
    __events__: tuple = ("on_release",)

    def on_release(self, touch: TouchBehavior) -> None:
        pass  # default no-op

    def on_touch_up(self, touch: TouchBehavior) -> bool | None:
        result = super().on_touch_up(touch)
        self.dispatch("on_release", touch)
        return cast(bool | None, result)


class TextSlider(MDBoxLayout):
    """
    A drop-in replacement for Slider that includes an attached Label
    to display the current value.
    """

    min = BoundedNumericProperty(0, min=-float("inf"), max=float("inf"))
    max = BoundedNumericProperty(100, min=-float("inf"), max=float("inf"))
    value = NumericProperty(50)
    step = NumericProperty(0)
    immediate_update = BooleanProperty(True)

    def __init__(self, range_like: None | Range | Interval = None, **kwargs: Any) -> None:
        if range_like is not None:
            super().__init__(
                orientation="horizontal",
                padding=dp(5),
                spacing=dp(5),
                min=range_like.minimum,
                max=range_like.maximum,
                **kwargs,
            )
        else:
            super().__init__(orientation="horizontal", padding=dp(5), spacing=dp(5), **kwargs)
        self.size_hint_x = 1
        self.size_hint_y = None
        self._block_updates = False
        self.bind(minimum_height=self.setter("height"))

        self._slider = SliderWithRelease(
            min=self.min, max=self.max, value=self.value, step=self.step
        )
        self._slider_handle = InstantMDSliderHandle()
        self._slider.add_widget(self._slider_handle)
        self._label = MDLabel(
            font_size=dp(18), size_hint_y=None, height=dp(30), size_hint_x=None, width=dp(40)
        )

        self._slider.hint = False
        self._slider.show_off = False
        self._slider.handle_anim_duration = 0

        self.add_widget(self._slider)
        self.add_widget(self._label)

        self.bind(
            min=self._update_slider_properties,
            max=self._update_slider_properties,
            step=self._update_slider_properties,
            value=self._update_slider_properties,
        )

        self._slider.bind(value=self._on_slider_value_change)
        self._slider.bind(on_release=self._on_slider_release)

        self._slider.bind(value=self._update_label_text)
        self._update_label_text()

    def _on_slider_release(self, _: Any, value: float) -> None:
        MDSlider.on_touch_up(self._slider, value)
        if not self.immediate_update:
            self.value = self._slider.value

    def _update_slider_properties(self, _: Any, value: float) -> None:
        """
        Called when min/max/step/value properties of LabeledSlider change.
        """

        self._slider.min = self.min
        self._slider.max = self.max

        if self._block_updates:
            return

        self._block_updates = True
        self._slider.value = self.value
        self._block_updates = False

    def _on_slider_value_change(self, _: Any, value: str) -> None:
        """
        Called when the internal slider's value changes.
        """

        if self._block_updates:
            return

        if self.immediate_update:
            self._block_updates = True
            self.value = value
            self._block_updates = False

    def _update_label_text(self, *args: Any) -> None:
        """
        Updates the Label text with the current value, handling formatting.
        """
        if self.step > 0:
            display_value = int(self._slider.value)
        else:
            display_value = round(self._slider.value, 2)

        self._label.text = f"{display_value}"

    @property
    def range(self) -> Range:
        return Range(self.min, self.max, self.step)

    @range.setter
    def range(self, range_like: Range | Interval) -> None:
        self.min = range_like.minimum
        self.max = range_like.maximum

        if isinstance(range_like, Range) and isinstance(range_like.maximum, int):
            self.step = range_like.increment


class BackgroundLayout(MDBoxLayout):
    rect: Rectangle

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        app = MDApp.get_running_app()

        assert self.canvas is not None

        with self.canvas.before:
            self.color_instruction = Color(rgba=app.theme_cls.backgroundColor)
            self.rect = Rectangle(size=self.size, pos=self.pos)

        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, instance: BackgroundLayout, value: Any) -> None:
        """Callback to update the rectangle's size and position."""
        self.rect.pos = instance.pos
        self.rect.size = instance.size


class StatusMessageDialog:
    dialog_open: bool = False

    @classmethod
    def show(cls, title_text: str, message_text: str) -> None:
        if cls.dialog_open:
            print(f"{title_text}: {message_text}")
            return

        cls.dialog_open = True

        dialog: MDDialog = MDDialog(
            MDDialogHeadlineText(text=title_text),
            MDDialogSupportingText(text=message_text),
            MDDialogButtonContainer(
                Widget(),
                MDButton(
                    MDButtonText(text="OK"), style="text", on_release=lambda _: dialog.dismiss()
                ),
                spacing="8dp",
            ),
        )

        # Define a proper callback function
        def on_dialog_dismiss(*args: Any) -> None:
            cls.dialog_open = False

        dialog.bind(on_dismiss=on_dialog_dismiss)
        dialog.open()


def show_status_message(title_text: str, message_text: str) -> None:
    StatusMessageDialog.show(title_text, message_text)
