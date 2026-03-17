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

import math

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QWidget
from PySide6.QtGui import QImage, QPainter
from PySide6.QtCore import QRectF, Slot


class Display(QGraphicsView):
    """
    This class implements an easy way to display images from a camera
    in a QT widgets window. It can be used for other QT widget applications
    as well.
    """

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.__scene = CustomGraphicsScene(self)
        self.setScene(self.__scene)

    @Slot(QImage)
    def on_image_received(self, image: QImage) -> None:
        self.__scene.set_image(image)
        self.update()


class CustomGraphicsScene(QGraphicsScene):
    def __init__(self, parent: Display) -> None:
        super().__init__(parent)
        self._parent = parent
        self._image = QImage()

    def set_image(self, image: QImage) -> None:
        self._image = image
        self.update()

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        # Display size
        display_width = self._parent.width()
        display_height = self._parent.height()

        # Image size
        image_width = self._image.width()
        image_height = self._image.height()

        # Return if we don't have an image yet
        if image_width == 0 or image_height == 0:
            return

        # Calculate aspect ratio of display
        ratio1 = display_width / display_height
        # Calculate aspect ratio of image
        ratio2 = image_width / image_height

        if ratio1 > ratio2:
            # The height with must fit to the display height.So h remains and w must be scaled down
            image_width = display_height * ratio2
            image_height = display_height
        else:
            # The image with must fit to the display width. So w remains and h must be scaled down
            image_width = display_width
            image_height = display_height / ratio2

        image_pos_x = -1.0 * (image_width / 2.0)
        image_pox_y = -1.0 * (image_height / 2.0)

        # Remove digits after point
        image_pos_x = math.trunc(image_pos_x)
        image_pox_y = math.trunc(image_pox_y)

        rect = QRectF(image_pos_x, image_pox_y, image_width, image_height)

        painter.drawImage(rect, self._image)
